
Ce module introduit une couche de sécurité dans les communications entre le drone et la station de base du projet T.A.I.L.S. (Tactical Aerial Insight & Localization Suite).
Il permet de chiffrer les données transmises par LoRa afin de garantir la confidentialité, l’intégrité et la protection contre les attaques par rejeu.

📁 Contenu ajouté

secure_sender.py — Génère et envoie des trames chiffrées (AES-GCM).

crypto.py — Contient la logique d’encryption et de décryption.

replay_guard.py — Met en place une protection contre la réutilisation de trames (anti-replay).

keys.json — Stocke localement les clés de chiffrement associées aux identifiants d’appareil.


Tests effectués

Des tests ont été réalisés en local à l’aide d’un mode dry-run (sans matériel LoRa) :

- Génération de trames chiffrées simulant l’envoi du drone.
- Vérification que la station peut déchiffrer correctement les trames valides.
- Rejet automatique des trames non valides ou modifiées.

Ces tests ont permis de confirmer que le chiffrement et le déchiffrement fonctionnent correctement en local.


Prochaines étapes

- Intégrer secure_sender.py sur le Raspberry Pi avec le module LoRa réel (SX126x).
- Remplacer les coordonnées GPS simulées par les données réelles du drone.
- Effectuer des tests en conditions réelles pour valider la transmission et le déchiffrement côté station.