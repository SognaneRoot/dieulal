# Récup/Télé — site web pour télécharger des vidéos

Site mobile pour récupérer des vidéos YouTube / Instagram / TikTok / Pinterest
en collant juste le lien. Basé sur Flask + yt-dlp.

## Option A — Le plus simple et 100% gratuit : héberger chez vous

C'est l'option la plus fiable : aucun service tiers, aucune limite, et les
plateformes ne bloquent pas votre IP personnelle (contrairement à beaucoup
d'hébergeurs gratuits, voir Option B).

1. Sur votre ordinateur (qui reste allumé) :
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
2. Trouvez l'IP locale de l'ordinateur :
   - Windows : `ipconfig` → ligne "Adresse IPv4"
   - Mac/Linux : `ifconfig` ou `ip a` → ligne "inet"
3. Sur votre téléphone, **connecté au même Wi-Fi**, ouvrez :
   ```
   http://VOTRE-IP-LOCALE:5000
   ```
4. Ajoutez la page à l'écran d'accueil (menu navigateur → "Ajouter à
   l'écran d'accueil") pour l'utiliser comme une app.

**Pour y accéder même hors de chez vous**, sans payer d'hébergement,
installez [Tailscale](https://tailscale.com) (gratuit) sur l'ordinateur et
sur le téléphone : ça crée un petit réseau privé entre vos appareils, et
vous accédez au site via l'IP Tailscale de l'ordinateur, de n'importe où.

## Option B — Hébergement cloud gratuit (accessible sans laisser le PC allumé)

[Render.com](https://render.com) propose un plan gratuit qui fonctionne avec
ce projet :

1. Mettez ce dossier dans un dépôt GitHub (privé si vous voulez).
2. Sur Render : **New → Web Service** → connectez le dépôt.
3. Choisissez **Docker** comme environnement (le `Dockerfile` fourni installe
   automatiquement ffmpeg, indispensable pour fusionner vidéo + audio).
4. Plan **Free**, puis déployez.
5. Ouvrez l'URL `https://votre-app.onrender.com` depuis votre téléphone,
   où que vous soyez.

**Limites à connaître du plan gratuit :**
- L'instance s'endort après ~15 min d'inactivité ; le premier chargement
  après une pause prend 30-60 secondes.
- YouTube bloque parfois les téléchargements venant d'IP d'hébergeurs cloud
  (datacenter). Si YouTube échoue sur Render mais fonctionne en local, c'est
  cette protection anti-bot — Instagram/TikTok/Pinterest sont en général
  moins strictes là-dessus.

## Structure du projet

```
webapp/
├── app.py              # serveur Flask
├── templates/index.html
├── static/style.css
├── static/app.js
├── requirements.txt
├── Procfile             # pour Render/Railway sans Docker
└── Dockerfile            # pour Render/Railway avec ffmpeg inclus
```

## ⚠️ À savoir

- Réservez cet outil à du contenu dont vous avez le droit de disposer
  (vos propres vidéos, contenu libre de droits, accord du créateur).
- Le téléchargement va à l'encontre des conditions d'utilisation de ces
  plateformes ; gardez un usage strictement personnel.
- N'exposez pas ce site publiquement sans protection (mot de passe) si vous
  ne voulez pas que d'autres personnes l'utilisent à votre place — il n'y a
  actuellement aucune authentification.
