# FEC Loader - Système de chargement automatique des fichiers FEC

## Description
Système automatisé pour charger les fichiers FEC (Fichier des Écritures Comptables) depuis un serveur SFTP vers une base de données PostgreSQL Azure. Le système détecte automatiquement les modifications des fichiers et évite les doublons.

## Fonctionnalités
- ✅ **Détection des modifications** : Utilise le hash MD5 et la date de modification
- ✅ **Prévention des doublons** : Supprime les anciennes données avant insertion
- ✅ **Rapport par email** : Envoi automatique du rapport d'exécution
- ✅ **Logging complet** : Fichier de log et sortie console
- ✅ **Gestion d'erreurs** : Traitement robuste des erreurs
- ✅ **Performance optimisée** : Utilise `execute_values` pour l'insertion en lot

## Structure du projet
```
airelles/
├── fec_loader_final.py          # Script principal
├── requirements.txt              # Dépendances Python
├── README.md                    # Cette documentation
├── fec_loader.log              # Fichier de log (généré automatiquement)
└── venv/                       # Environnement virtuel Python
```

## Configuration

### Base de données PostgreSQL
- **Host** : opsserveur.postgres.database.azure.com
- **Database** : airelles
- **Schema** : bronze
- **Tables** :
  - `bronze.fec_raw` : Données brutes des fichiers FEC
  - `bronze.fec_file_status` : Statut des fichiers traités

### Email
- **SMTP** : smtp.gmail.com:587
- **From** : enzoberbeche@gmail.com
- **To** : enzoberbeche@opsconseil.com

### Répertoire source
- **Chemin SFTP** : /sftp/fecclient/Airelles/Fec
- **Format** : Fichiers .txt avec encodage latin-1

## Installation

1. **Créer l'environnement virtuel** :
```bash
cd /home/adminenzo/airelles
python3 -m venv venv
source venv/bin/activate
```

2. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

3. **Tester la connexion** :
```bash
python fec_loader_final.py
```

## Utilisation

### Exécution manuelle
```bash
cd /home/adminenzo/airelles
source venv/bin/activate
python fec_loader_final.py
```

### Exécution automatique (Cron)
Pour exécuter tous les jours à 6h00 :
```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne
0 6 * * * cd /home/adminenzo/airelles && source venv/bin/activate && python fec_loader_final.py
```

## Structure des données

### Table `bronze.fec_raw`
Toutes les colonnes sont stockées en VARCHAR pour éviter les problèmes de conversion :

| Colonne | Type | Description |
|---------|------|-------------|
| id | SERIAL | Clé primaire |
| file_name | VARCHAR(100) | Nom du fichier source |
| file_hash | VARCHAR(64) | Hash MD5 du fichier |
| file_modified | TIMESTAMP | Date de modification |
| loaded_at | TIMESTAMP | Date de chargement |
| journal_code | VARCHAR(50) | Code journal |
| journal_lib | VARCHAR(255) | Libellé journal |
| ecriture_num | VARCHAR(50) | Numéro écriture |
| ecriture_date | VARCHAR(50) | Date écriture |
| compte_num | VARCHAR(50) | Numéro compte |
| compte_lib | VARCHAR(255) | Libellé compte |
| comp_aux_num | VARCHAR(100) | Numéro compte auxiliaire |
| comp_aux_lib | VARCHAR(500) | Libellé compte auxiliaire |
| piece_ref | VARCHAR(100) | Référence pièce |
| piece_date | VARCHAR(50) | Date pièce |
| ecriture_lib | TEXT | Libellé écriture |
| debit | VARCHAR(50) | Débit |
| credit | VARCHAR(50) | Crédit |
| ecriture_let | VARCHAR(50) | Lettrage écriture |
| date_let | VARCHAR(50) | Date lettrage |
| valid_date | VARCHAR(50) | Date validation |
| montant_devise | VARCHAR(50) | Montant devise |
| idevise | VARCHAR(50) | ID devise |
| code_etbt | VARCHAR(50) | Code établissement |
| type_piece | VARCHAR(50) | Type pièce |
| edate | VARCHAR(50) | Date édition |
| ref_origine | VARCHAR(100) | Référence origine |
| numero | VARCHAR(100) | Numéro |
| numero_def | VARCHAR(100) | Numéro définitif |
| origine_lot | VARCHAR(100) | Origine lot |
| code_etbt2 | VARCHAR(50) | Code établissement 2 |

### Table `bronze.fec_file_status`
Suivi des fichiers traités :

| Colonne | Type | Description |
|---------|------|-------------|
| file_name | VARCHAR(100) | Nom du fichier (PK) |
| file_path | TEXT | Chemin complet |
| last_hash | VARCHAR(64) | Dernier hash connu |
| last_modified | TIMESTAMP | Dernière modification connue |
| last_loaded | TIMESTAMP | Dernier chargement |
| status | VARCHAR(20) | Statut (loaded/error) |
| error_message | TEXT | Message d'erreur si applicable |

## Logs et monitoring

### Fichier de log
- **Emplacement** : `/home/adminenzo/airelles/fec_loader.log`
- **Rotation** : Automatique (géré par Python logging)
- **Niveau** : INFO

### Rapport email
Le système envoie automatiquement un rapport par email contenant :
- Nombre de fichiers traités
- Nombre de fichiers modifiés
- Nombre de fichiers ignorés
- Nombre total de lignes chargées
- Liste des erreurs éventuelles
- Durée d'exécution

## Gestion des erreurs

Le système gère plusieurs types d'erreurs :
- **Erreurs de connexion** : Base de données, SFTP
- **Erreurs de lecture** : Fichiers corrompus, encodage
- **Erreurs de chargement** : Contraintes de base de données
- **Erreurs d'email** : Problèmes SMTP

Toutes les erreurs sont loggées et incluses dans le rapport email.

## Performance

- **Insertion optimisée** : Utilise `execute_values` avec des lots de 1000 lignes
- **Détection efficace** : Hash MD5 pour détecter les modifications
- **Prévention des doublons** : Suppression avant insertion
- **Gestion mémoire** : Traitement par lots pour les gros fichiers

## Maintenance

### Vérifier le statut
```bash
# Voir les logs récents
tail -f fec_loader.log

# Vérifier les fichiers traités
psql -h opsserveur.postgres.database.azure.com -U doadmin -d airelles -c "SELECT * FROM bronze.fec_file_status ORDER BY last_loaded DESC;"
```

### Nettoyer les logs
```bash
# Archiver les anciens logs
mv fec_loader.log fec_loader_$(date +%Y%m%d).log
```

## Support

Pour toute question ou problème :
1. Vérifier les logs dans `fec_loader.log`
2. Consulter le rapport email
3. Vérifier la connectivité réseau et base de données

---
*Système développé pour Airelles - Chargement automatique des fichiers FEC*