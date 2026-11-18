// Démarre le serveur construit, toujours lié à 127.0.0.1 : un HOST venu de l'extérieur est ignoré.
process.env.HOST = '127.0.0.1';
process.env.PORT ??= '3000';
// Sans cette origine, l'adaptateur suppose https et SvelteKit refuse tous les formulaires envoyés en http.
process.env.ORIGIN = `http://127.0.0.1:${process.env.PORT}`;
console.log(`Tableau de bord : ${process.env.ORIGIN}`);
await import('../build/index.js');
