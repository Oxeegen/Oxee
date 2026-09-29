<h1 align="center">Oxee</h1>

<p align="center">
  <a href="../README.md">English</a> · <a href="README.fr.md">Français</a>
</p>

<p align="center">
  <img src="../brand/assets/oxee-icon-1024.png" alt="Icône Oxee" width="96" height="96" />
</p>

<p align="center">
  <strong>Oxeegen Intelligence dans votre poche : l'application native iPhone et Android de votre espace IA Oxeegen.</strong>
</p>

<p align="center">
  <img alt="Dernière version" src="https://img.shields.io/github/v/release/Oxeegen/Oxee?display_name=tag&color=5A21F2" />
  <img alt="Licence : GPL-3.0" src="https://img.shields.io/badge/Licence-GPL%203.0-16A34A" />
</p>

<br>

Oxee est l'application mobile d'**Oxeegen Intelligence**, l'espace de
conversation IA d'Oxeegen. Choisissez votre région, connectez-vous avec votre
compte Oxeegen : vos modèles, conversations, notes et connaissances sont là,
comme sur le web, mais pensés pour le téléphone : un streaming qui continue
quand l'application passe en arrière-plan, la voix, le menu de partage, les
widgets d'écran d'accueil et les raccourcis Siri.

## Régions

Oxee se connecte uniquement aux déploiements d'Oxeegen. Choisissez celui de
votre compte à la première ouverture ; vous pourrez en changer ensuite dans
**Réglages → Région**.

| Région | Serveur | Pour |
| --- | --- | --- |
| **Oxeegen US** | `ai.oxeegen.com` | Comptes hébergés aux États-Unis |
| **Oxeegen FR** | `ia.oxeegen.fr` | Comptes hébergés en France |

Chaque région a ses propres comptes et conversations. Changer de région vous
déconnecte de l'une et vous connecte à l'autre ; rien n'est copié entre elles.

## Ce que vous obtenez

### Une conversation pensée pour le mobile

Streaming mot à mot, un fil qui reste en place pendant que la réponse
s'écrit, et de longues conversations qui s'ouvrent sans ralentir. Recherche,
dossiers, conversations épinglées et conversations temporaires qui ne
laissent aucune trace.

### Des réponses lisibles sur un téléphone

Un rendu natif, pas une page web dans un cadre : code coloré avec copie,
diagrammes Mermaid, LaTeX, sections de raisonnement et d'appels d'outils
dépliables, citations avec fiches de sources, suggestions de relance et
graphiques.

### Tout votre espace de travail

| Domaine | Contenu |
| --- | --- |
| Modèles et espace de travail | Modèles, connaissances, prompts, outils et compétences en écrans natifs, selon les droits de votre compte |
| Fichiers et médias | Envoi de fichiers, réutilisation de fichiers déjà sur le serveur, images dans les prompts, collage d'images, pièces jointes audio |
| Notes | Enregistrement automatique, épinglage, titres et améliorations par l'IA, enregistrement audio, disponibles hors ligne |
| Canaux | Fils de discussion et réactions, quand votre espace les propose |
| Voix | Dictée avec reconnaissance vocale sur l'appareil ou sur le serveur, et un mode appel vocal mains libres |
| Écran d'accueil | Widgets iOS et Android (nouvelle conversation, micro, appareil photo, photos, presse-papiers), actions rapides, raccourcis Siri |
| Partage | Envoyez du texte, des liens et des images depuis n'importe quelle application directement dans un prompt |
| Personnalisation | Thèmes clair, sombre et système, palettes d'accent, interfaces natives iOS et Material, retours haptiques |
| Langues | Français, anglais, allemand, espagnol, italien, néerlandais, polonais, tchèque, slovaque, russe, japonais, coréen, chinois simplifié et traditionnel |

Des fonctions comme la recherche web, la génération d'images, les canaux et
les notes apparaissent lorsqu'elles sont activées pour votre espace Oxeegen.

## Premiers pas

1. Installez Oxee sur votre iPhone ou votre téléphone Android.
2. Ouvrez-la et choisissez **Oxeegen US** ou **Oxeegen FR**.
3. Connectez-vous avec votre compte Oxeegen (e-mail et mot de passe, ou
   l'identifiant de l'annuaire de votre entreprise).
4. Choisissez un modèle et commencez à discuter.

Pas encore de compte ? Contactez [Oxeegen](https://www.oxeegen.com).

## Confidentialité

- Vos conversations sont dans votre espace Oxeegen. L'application en garde
  une copie sur l'appareil pour les ouvrir tout de suite ; les notes et les
  brouillons fonctionnent aussi hors ligne.
- Les jetons de connexion sont conservés dans le trousseau (Keychain) sur iOS
  et le Keystore sur Android.
- Aucun SDK tiers d'analyse ou de publicité.
- L'application ne communique qu'avec la région Oxeegen que vous avez choisie.

Tous les détails dans [PRIVACY_POLICY.md](../PRIVACY_POLICY.md) (en anglais).

## Compiler depuis les sources

Voir **[docs/BUILDING.md](BUILDING.md)** (en anglais) pour les prérequis, la
génération de code, les tests et les versions de production.

```bash
git clone --recursive https://github.com/Oxeegen/Oxee.git
cd Oxee
flutter pub get
dart run build_runner build
flutter run -d android   # ou : flutter run -d ios (nécessite un Mac)
```

## Retours

Un bug ou une idée ? Ouvrez une
[issue](https://github.com/Oxeegen/Oxee/issues).

## Licence

Oxee est un logiciel libre sous
[licence publique générale GNU v3.0](../LICENSE). Voir [NOTICE](../NOTICE).

Maintenu par [Oxeegen](https://www.oxeegen.com).
