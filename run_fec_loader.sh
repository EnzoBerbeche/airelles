#!/bin/bash
# Wrapper pour FEC Loader dans le cron

# Aller dans le répertoire du projet
cd /home/adminenzo/airelles

# Activer l'environnement virtuel
source venv/bin/activate

# Exécuter le script principal
python fec_loader_final.py

# Capturer le code de sortie
exit_code=$?

# Log du code de sortie
echo "$(date): FEC Loader terminé avec le code $exit_code" >> /home/adminenzo/airelles/cron.log

exit $exit_code
