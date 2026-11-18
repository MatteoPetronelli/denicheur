#!/usr/bin/env python3
"""Test de couverture des API France Travail pour le projet Dénicheur.

Deux tests indépendants, avec un jeton OAuth par API (chaque API a son propre scope) :

  1. API « Offres d'emploi v2 » : y a-t-il des offres de STAGE et d'APPRENTISSAGE
     dans un rayon de 25 km autour de Mareil-Marly (78750) ?
  2. API « La Bonne Boite v2 » : entreprises à fort potentiel d'embauche (candidatures
     spontanées) dans le même rayon.

Utilisation :
    export FT_CLIENT_ID="..."        # identifiant client de ton application sur francetravail.io
    export FT_CLIENT_SECRET="..."
    py scripts/test_france_travail.py

Variables facultatives (si un scope est refusé) :
    FT_SCOPE_OFFRES   ex. "api_offresdemploiv2 o2dsoffre"
    FT_SCOPE_LBB      ex. "api_labonneboitev2"
    FT_TEST=offres|lbb|entreprises|alternance   pour ne lancer qu'un test
    LBA_API_KEY       clé d'API de api.apprentissage.beta.gouv.fr (test 4, alternance)

Aucune dépendance externe. Résultats bruts dans data/ft_test_results.json.
"""
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
API_OFFRES = "https://api.francetravail.io/partenaire/offresdemploi/v2"
API_LBB = "https://api.francetravail.io/partenaire/labonneboite/v2"
GEO = "https://geo.api.gouv.fr/communes"
RAYON_KM = 25


def http(url, data=None, headers=None, timeout=30):
    """Retourne (statut, en-têtes, corps). Ne lève pas d'exception :
    erreur HTTP -> son code ; erreur réseau ou délai dépassé -> statut 0."""
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:  # inclut TimeoutError
        return 0, {}, f"erreur réseau : {e}"


def credentials():
    cid, secret = os.environ.get("FT_CLIENT_ID"), os.environ.get("FT_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Définis FT_CLIENT_ID et FT_CLIENT_SECRET (variables d'environnement).")
    return cid, secret


def get_token(scopes_a_essayer):
    """Essaie chaque scope dans l'ordre. Retourne (jeton, scope_utilisé) ou (None, None).

    Les scopes ne sont pas affichés dans la console francetravail.io : ce sont des noms
    conventionnels (api_<nom>v<n>), parfois suivis d'un scope complémentaire.
    """
    cid, secret = credentials()
    for scope in scopes_a_essayer:
        scope = scope.replace("{cid}", cid)
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": cid,
            "client_secret": secret,
            "scope": scope,
        }).encode()
        status, _, text = http(TOKEN_URL, data=body,
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
        shown = scope.replace(cid, "<client_id>")
        if status == 200:
            info = json.loads(text)
            accorde = str(info.get("scope")).replace(cid, "<client_id>")
            print(f"  jeton obtenu pour « {shown} » (scope accordé : {accorde}, "
                  f"expire dans {info.get('expires_in')} s)")
            return info["access_token"], scope
        print(f"  scope refusé « {shown} » (HTTP {status}) : {text[:160]}")
    return None, None


ADRESSE = "https://api-adresse.data.gouv.fr/search/"
# Ripiego approximatif (centre de Mareil-Marly) si aucun service de géocodage ne répond.
LAT_DEFAUT, LON_DEFAUT = 48.881, 2.089


def centre_commune(nom="Mareil-Marly", cp="78750"):
    """Retourne (code INSEE, latitude, longitude).

    1. geo.api.gouv.fr (2 essais, délai 60 s)
    2. api-adresse.data.gouv.fr (BAN)
    3. Variable FT_COMMUNE (code INSEE saisi à la main) + coordonnées approximatives
    """
    q = urllib.parse.urlencode({"nom": nom, "codePostal": cp, "fields": "nom,code,centre", "limit": 1})
    for essai in (1, 2):
        status, _, text = http(f"{GEO}?{q}", timeout=60)
        if status == 200 and json.loads(text):
            c = json.loads(text)[0]
            lon, lat = c["centre"]["coordinates"]
            print(f"Commune : {c['nom']} (INSEE {c['code']}) — lat {lat:.4f}, lon {lon:.4f}")
            return c["code"], lat, lon
        print(f"  geo.api.gouv.fr indisponible (essai {essai}, statut {status})")

    q = urllib.parse.urlencode({"q": nom, "postcode": cp, "type": "municipality", "limit": 1})
    status, _, text = http(f"{ADRESSE}?{q}", timeout=60)
    if status == 200:
        feats = json.loads(text).get("features", [])
        if feats:
            props, lon_lat = feats[0]["properties"], feats[0]["geometry"]["coordinates"]
            print(f"Commune (api-adresse) : {props.get('city')} (INSEE {props.get('citycode')})")
            return props["citycode"], lon_lat[1], lon_lat[0]
    print(f"  api-adresse.data.gouv.fr indisponible (statut {status})")

    insee = os.environ.get("FT_COMMUNE")
    if insee:
        print(f"Ripiego : code INSEE {insee} fourni par FT_COMMUNE, coordonnées approximatives.")
        return insee, LAT_DEFAUT, LON_DEFAUT
    sys.exit("Impossible de déterminer la commune (réseau ?). Réessaie, ou fournis le code INSEE : "
             "export FT_COMMUNE=<code INSEE de Mareil-Marly>  (ou  $env:FT_COMMUNE=\"...\" sous PowerShell)")


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


# ------------------------------------------------------------------ Offres d'emploi v2

def referentiel(token, nom):
    status, _, text = http(f"{API_OFFRES}/referentiel/{nom}",
                           headers={"Authorization": f"Bearer {token}"})
    if status != 200:
        print(f"  [référentiel {nom}] HTTP {status} (chemin à vérifier dans la doc)")
        return []
    return json.loads(text)


def recherche_offres(token, **params):
    """Première page (150 offres max). Retourne (total, liste d'offres)."""
    params.setdefault("range", "0-149")
    status, headers, text = http(f"{API_OFFRES}/offres/search?{urllib.parse.urlencode(params)}",
                                 headers={"Authorization": f"Bearer {token}"})
    time.sleep(0.15)  # limite publiée : 10 appels par seconde
    if status == 204 or not text.strip():
        return 0, []
    if status not in (200, 206):
        print(f"  HTTP {status} : {text[:200]}")
        return 0, []
    total = None
    cr = next((v for k, v in headers.items() if k.lower() == "content-range"), "")
    if "/" in cr:
        try:
            total = int(cr.split("/")[-1])
        except ValueError:
            pass
    offres = json.loads(text).get("resultats", [])
    return (total if total is not None else len(offres)), offres


def resume_offres(titre, total, offres, resultats):
    types = Counter(f"{o.get('typeContrat')}|{o.get('natureContrat')}" for o in offres)
    stage_like = [o for o in offres
                  if any(m in (o.get("intitule", "") + " " + o.get("description", "")[:300]).lower()
                         for m in ("stage", "stagiaire"))]
    print(f"\n== {titre}")
    print(f"   total annoncé : {total} | analysées : {len(offres)} | mentionnent 'stage' : {len(stage_like)}")
    for k, n in types.most_common(5):
        print(f"   contrat|nature : {k} × {n}")
    for o in offres[:5]:
        lieu = (o.get("lieuTravail") or {}).get("libelle", "?")
        print(f"   - {o.get('intitule', '?')[:70]} | {lieu} | {o.get('natureContrat')} | {o.get('typeContratLibelle')}")
    resultats[titre] = {"total": total, "offres": offres}


def test_offres(commune, resultats):
    print("\n########## TEST 1 : API Offres d'emploi v2 ##########")
    scopes = ([os.environ["FT_SCOPE_OFFRES"]] if os.environ.get("FT_SCOPE_OFFRES") else
              ["api_offresdemploiv2 o2dsoffre", "api_offresdemploiv2",
               "application_{cid} api_offresdemploiv2 o2dsoffre"])
    token, _ = get_token(scopes)
    if not token:
        print("  → Test 1 ignoré : aucun scope accepté. Vérifie que l'application est abonnée "
              "à « Offres d'emploi v2 » sur francetravail.io.")
        return
    zone = {"commune": commune, "distance": RAYON_KM}

    print("\nRéférentiels :")
    types = referentiel(token, "typesContrats")
    natures = referentiel(token, "naturesContrats")
    for nom, ref in (("typesContrats", types), ("naturesContrats", natures)):
        print(f"  {nom} : " + ", ".join(f"{x.get('code')}={x.get('libelle')}" for x in ref[:25]))

    t, o = recherche_offres(token, **zone)
    resume_offres("Toutes offres (contrôle de la zone)", t, o, resultats)

    for mots in ("stage", "stagiaire", "stage développeur", "stage informatique"):
        t, o = recherche_offres(token, motsCles=mots, **zone)
        resume_offres(f"Mots-clés « {mots} »", t, o, resultats)

    for mots in ("alternance développeur", "apprentissage développeur",
                 "alternance informatique", "alternance web"):
        t, o = recherche_offres(token, motsCles=mots, **zone)
        resume_offres(f"Mots-clés « {mots} »", t, o, resultats)

    for n in natures:
        lib = (n.get("libelle") or "").lower()
        if "apprentissage" in lib or "professionnalisation" in lib:
            for mots in (None, "développeur"):
                p = dict(zone, natureContrat=n["code"])
                if mots:
                    p["motsCles"] = mots
                t, o = recherche_offres(token, **p)
                resume_offres(f"Nature « {n['libelle']} »" + (f" + « {mots} »" if mots else ""),
                              t, o, resultats)


# ------------------------------------------------------------------ La Bonne Boite v2

class AccesRefuse(Exception):
    """L'API répond 403 alors que le jeton est valide (accès non habilité)."""


def recherche_lbb(token, **params):
    """GET /recherche (doc : latitude, longitude, distance, job, rome, naf, page, page_size ≤ 100)."""
    q = urllib.parse.urlencode(params, doseq=True)
    for tentative in (1, 2, 3):
        status, headers, text = http(f"{API_LBB}/recherche?{q}",
                                     headers={"Authorization": f"Bearer {token}"})
        time.sleep(1.5)  # l'API limite le débit : on reste lent
        if status == 429 and tentative < 3:
            attente = next((v for k, v in headers.items() if k.lower() == "retry-after"), "5")
            print(f"  HTTP 429 (trop de requêtes) : nouvelle tentative dans {attente} s")
            time.sleep(float(attente) if str(attente).isdigit() else 5)
            continue
        break
    if status == 403:
        raise AccesRefuse(text[:200])
    if status != 200:
        print(f"  HTTP {status} : {text[:250]}")
        return None
    return json.loads(text)


def test_lbb(lat, lon, resultats):
    print("\n########## TEST 2 : API La Bonne Boite v2 ##########")
    scopes = ([os.environ["FT_SCOPE_LBB"]] if os.environ.get("FT_SCOPE_LBB") else
              ["api_labonneboitev2", "application_{cid} api_labonneboitev2"])
    token, _ = get_token(scopes)
    if not token:
        print("  → Test 2 ignoré : aucun scope accepté. Vérifie que l'application est abonnée "
              "à « La Bonne Boite v2 ».")
        return
    base = {"latitude": lat, "longitude": lon, "distance": RAYON_KM, "page_size": 50,
            "sort_by": "hiring_potential", "sort_direction": "desc"}
    essais = [
        ("Métier libre « développeur informatique »", {"job": "développeur informatique"}),
        ("Métier libre « informatique »", {"job": "informatique"}),
        # ROME 3.0 « Études et développement informatique » : à vérifier dans ROME 4.0
        ("ROME M1805", {"rome": ["M1805"]}),
    ]
    for titre, extra in essais:
        try:
            data = recherche_lbb(token, **base, **extra)
        except AccesRefuse as e:
            print(f"  → HTTP 403 : {e}\n"
                  "  Le jeton est valide mais l'API refuse la requête. La Bonne Boite semble être une API "
                  "à accès conditionné (habilitation à demander à France Travail). Voir les consignes.")
            return
        if data is None:
            continue
        items = data.get("items") or []
        print(f"\n== {titre}\n   hits : {data.get('hits')} | page : {len(items)}")
        for it in items[:10]:
            loc = it.get("location") or {}
            d = (haversine_km(lat, lon, loc["lat"], loc["lon"])
                 if "lat" in loc and "lon" in loc else float("nan"))
            print(f"   - {str(it.get('company_name'))[:38]:38} | {it.get('city')} ({d:.1f} km) | "
                  f"potentiel {it.get('hiring_potential', 0):.0f} | "
                  f"{str(it.get('naf_label'))[:40]} | effectif {it.get('headcount_min')}-{it.get('headcount_max')}")
        resultats[f"LBB {titre}"] = data


# ------------------------------------------------------------------ Recherche d'entreprises (sans clé)

def test_entreprises(lat, lon, resultats):
    """API publique recherche-entreprises.api.gouv.fr : aucune clé, aucun scope.
    Paramètres utilisés (à vérifier dans la doc si une erreur apparaît) :
    activite_principale, lat, long, radius (km), etat_administratif, per_page (≤ 25)."""
    print("\n########## TEST 3 : Recherche d'entreprises (sans clé) ##########")
    for naf in ("62.01Z", "62.02A"):
        q = urllib.parse.urlencode({"activite_principale": naf, "lat": lat, "long": lon,
                                    "radius": RAYON_KM, "etat_administratif": "A", "per_page": 25})
        status, _, text = http(f"https://recherche-entreprises.api.gouv.fr/search?{q}", timeout=60)
        time.sleep(0.3)
        if status != 200:
            print(f"  NAF {naf} : HTTP {status} {text[:200]}")
            continue
        data = json.loads(text)
        res = data.get("results", [])
        print(f"\n== NAF {naf} : {data.get('total_results')} entreprises dans {RAYON_KM} km "
              f"(première page : {len(res)})")
        for r in res[:10]:
            s = r.get("siege") or {}
            d = (haversine_km(lat, lon, float(s["latitude"]), float(s["longitude"]))
                 if s.get("latitude") and s.get("longitude") else float("nan"))
            print(f"   - {str(r.get('nom_complet'))[:40]:40} | {s.get('commune')} ({d:.1f} km) | "
                  f"effectif {r.get('tranche_effectif_salarie')}")
        resultats[f"Entreprises NAF {naf}"] = data


# ------------------------------------------------------------------ La bonne alternance (offres d'alternance)

API_LBA = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def test_alternance(lat, lon, resultats):
    """API « Recherche d'opportunités d'emploi en alternance » (La bonne alternance).
    Clé d'API gratuite, créée sur api.apprentissage.beta.gouv.fr (compte -> clé production).
    Limite : 60 appels/minute. Résultats : 150 max par source."""
    print("\n########## TEST 4 : La bonne alternance (offres d'alternance) ##########")
    cle = os.environ.get("LBA_API_KEY")
    if not cle:
        print("  → ignoré : définis LBA_API_KEY (clé créée sur api.apprentissage.beta.gouv.fr).")
        return
    base = {"latitude": lat, "longitude": lon, "radius": RAYON_KM}
    essais = [
        ("ROME M1805/M1806/M1807 (développement informatique)", {"romes": "M1805,M1806,M1807"}),
        ("ROME informatique + niveau cible 6 (Bac+3)", {"romes": "M1805,M1806,M1807", "target_diploma_level": "6"}),
        ("ROME informatique + niveau cible 7 (Bac+5)", {"romes": "M1805,M1806,M1807", "target_diploma_level": "7"}),
    ]
    for titre, extra in essais:
        q = urllib.parse.urlencode({**base, **extra})
        status, headers, text = http(f"{API_LBA}?{q}", headers={"Authorization": f"Bearer {cle}"}, timeout=60)
        time.sleep(1.2)  # 60 appels / minute
        if status != 200:
            msg = {401: "clé absente, invalide ou expirée", 403: "habilitation manquante (inattendu en lecture)",
                   429: "limite de débit atteinte"}.get(status, "")
            print(f"\n== {titre}\n   HTTP {status} {msg} : {text[:200]}")
            continue
        data = json.loads(text)
        jobs, recruteurs = data.get("jobs") or [], data.get("recruiters") or []
        sources = Counter((j.get("identifier") or {}).get("partner_label") for j in jobs)
        urgentes = [j for j in jobs if (j.get("contract") or {}).get("start_type") == "des_que_possible"]
        print(f"\n== {titre}")
        print(f"   offres : {len(jobs)} | dont « dès que possible » : {len(urgentes)} | "
              f"entreprises à fort potentiel (spontanées) : {len(recruteurs)}")
        for k, n in sources.most_common():
            print(f"   source : {k} × {n}")
        for j in jobs[:10]:
            w, c = j.get("workplace") or {}, j.get("contract") or {}
            titre_offre = ((j.get("offer") or {}).get("title") or "?")[:55]
            print(f"   - {titre_offre} | {str(w.get('name'))[:28]} | début : {c.get('start_type') or c.get('start')} | "
                  f"durée : {c.get('duration')} mois | {','.join(c.get('type') or [])} | {c.get('remote')}")
        for r in recruteurs[:5]:
            w = r.get("workplace") or {}
            print(f"   · spontanée : {str(w.get('name'))[:35]} | effectif {w.get('size')} | {w.get('website')}")
        resultats[f"LBA {titre}"] = data


def main():
    cible = os.environ.get("FT_TEST", "").lower()
    commune, lat, lon = centre_commune()
    resultats = {}
    if cible in ("", "offres"):
        test_offres(commune, resultats)
    if cible in ("", "lbb"):
        test_lbb(lat, lon, resultats)
    if cible in ("", "entreprises"):
        test_entreprises(lat, lon, resultats)
    if cible in ("", "alternance"):
        test_alternance(lat, lon, resultats)
    sortie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "ft_test_results.json")
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    print("\nRésultats bruts enregistrés dans data/ft_test_results.json")


if __name__ == "__main__":
    main()
