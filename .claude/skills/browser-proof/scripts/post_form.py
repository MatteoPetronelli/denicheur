#!/usr/bin/env python3
"""Post a server-rendered HTML form the way a browser would, without a browser. Stdlib only.

    python post_form.py URL field=value [field=value ...] [--index N] [--then URL]

Fetches URL, picks the form that contains every named field, keeps its hidden inputs (CSRF tokens,
framework action ids such as Next.js `$ACTION_*`), posts it as multipart/form-data to the form's
action (or to URL), and prints: status, redirect target, and the text of any role="alert" element.
Cookies are kept between the requests, so `--then http://host/admin` checks that a login really opened a session.

Importable: `from post_form import Session; s = Session("http://localhost:3000"); s.post("/login", {...})`.
"""

import argparse
import html
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # we want to see the redirect, not follow it


class Session:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), _NoRedirect)

    def _open(self, req):
        try:
            r = self.opener.open(req)
            return r.status, r.headers.get("Location"), r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Location"), e.read().decode("utf-8", "replace")

    def get(self, path):
        return self._open(self.base + path)

    def post(self, path, fields, index=0):
        """Returns (status, location, body). Raises LookupError if no form holds all the fields."""
        _, _, page = self.get(path)
        forms = re.findall(r"<form([^>]*)>(.*?)</form>", page, flags=re.S)
        matches = [(attrs, body) for attrs, body in forms if all(f'name="{k}"' in body for k in fields)]
        if len(matches) <= index:
            raise LookupError(f"{len(matches)} form(s) on {path} contain the fields {list(fields)}; index {index} asked")
        attrs, body = matches[index]
        # Hidden inputs, with or without a value: a missing one makes the server reject the post.
        hidden = {
            html.unescape(n): html.unescape(v)
            for n, v in re.findall(r'<input type="hidden" name="([^"]+)"(?: value="([^"]*)")?', body)
        }
        action = re.search(r'action="([^"]*)"', attrs)
        target = urllib.parse.urljoin(self.base + path, html.unescape(action.group(1))) if action and action.group(1) else self.base + path
        data = {**hidden, **fields}
        boundary = uuid.uuid4().hex
        payload = "".join(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in data.items()
        ) + f"--{boundary}--\r\n"
        req = urllib.request.Request(
            target,
            data=payload.encode("utf-8"),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Origin": self.base},
        )
        return self._open(req)


def alerts(body):
    """The text of every role="alert" element (how accessible forms report an error)."""
    found = re.findall(r'role="alert"[^>]*>(.*?)</', body, flags=re.S)
    return [html.unescape(re.sub(r"<!--.*?-->|<[^>]+>", "", a)).strip() for a in found if a.strip()]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("fields", nargs="*", help="field=value")
    p.add_argument("--index", type=int, default=0, help="which matching form, when several share the fields")
    p.add_argument("--then", help="URL to GET afterwards with the same cookies (give a full URL under Git Bash)")
    a = p.parse_args()

    u = urllib.parse.urlsplit(a.url)
    s = Session(f"{u.scheme}://{u.netloc}")
    fields = dict(f.split("=", 1) for f in a.fields)
    try:
        status, location, body = s.post(u.path or "/", fields, a.index)
    except LookupError as e:
        sys.exit(str(e))
    out = sys.stdout
    out.reconfigure(encoding="utf-8")
    print(f"POST {a.url} -> {status}" + (f"  redirect: {location}" if location else ""))
    for alert in alerts(body):
        print(f"  alert: {alert}")
    if a.then:
        # A full URL is accepted (and safer): Git Bash rewrites a bare "/admin" into a Windows path.
        st, loc, _ = s.get(urllib.parse.urlsplit(a.then).path if "://" in a.then else a.then)
        print(f"GET  {a.then} -> {st}" + (f"  redirect: {loc}" if loc else ""))


if __name__ == "__main__":
    main()
