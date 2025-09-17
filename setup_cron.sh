#!/bin/bash
# Script de configuration du cron pour FEC Loader

echo "=== Configuration du cron pour FEC Loader ==="

# Vérifier que le script principal existe
if [ ! -f "/home/adminenzo/airelles/fec_loader_final.py" ]; then
    echo "ERREUR: Le script fec_loader_final.py n'existe pas"
    exit 1
fi

# Rendre le script exécutable
chmod +x /home/adminenzo/airelles/fec_loader_final.py

# Créer le script wrapper pour le cron
cat > /home/adminenzo/airelles/run_fec_loader.sh << 'EOF'
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
EOF

# Rendre le wrapper exécutable
chmod +x /home/adminenzo/airelles/run_fec_loader.sh

echo "Script wrapper créé: /home/adminenzo/airelles/run_fec_loader.sh"

# Afficher les options de cron
echo ""
echo "=== Options de configuration cron ==="
echo ""
echo "1. Exécution quotidienne à 6h00 (recommandé):"
echo "   0 6 * * * /home/adminenzo/airelles/run_fec_loader.sh"
echo ""
echo "2. Exécution toutes les 6 heures:"
echo "   0 */6 * * * /home/adminenzo/airelles/run_fec_loader.sh"
echo ""
echo "3. Exécution du lundi au vendredi à 6h00:"
echo "   0 6 * * 1-5 /home/adminenzo/airelles/run_fec_loader.sh"
echo ""
echo "4. Exécution toutes les 30 minutes (pour tests):"
echo "   */30 * * * * /home/adminenzo/airelles/run_fec_loader.sh"
echo ""

# Proposer d'ajouter automatiquement la tâche cron
read -p "Voulez-vous ajouter automatiquement la tâche cron quotidienne à 6h00 ? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Sauvegarder le crontab actuel
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
    
    # Ajouter la nouvelle tâche
    (crontab -l 2>/dev/null; echo "0 6 * * * /home/adminenzo/airelles/run_fec_loader.sh") | crontab -
    
    echo "✓ Tâche cron ajoutée avec succès"
    echo "✓ Sauvegarde du crontab précédent créée"
    
    # Afficher le crontab actuel
    echo ""
    echo "Crontab actuel:"
    crontab -l
else
    echo "Pour ajouter manuellement la tâche cron:"
    echo "1. Exécuter: crontab -e"
    echo "2. Ajouter la ligne: 0 6 * * * /home/adminenzo/airelles/run_fec_loader.sh"
    echo "3. Sauvegarder et quitter"
fi

echo ""
echo "=== Configuration terminée ==="
echo ""
echo "Pour tester le système:"
echo "  /home/adminenzo/airelles/run_fec_loader.sh"
echo ""
echo "Pour voir les logs:"
echo "  tail -f /home/adminenzo/airelles/fec_loader.log"
echo "  tail -f /home/adminenzo/airelles/cron.log"
echo ""
echo "Pour désactiver le cron:"
echo "  crontab -e  # puis supprimer la ligne correspondante"
