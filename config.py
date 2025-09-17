# Configuration pour FEC Loader
# Modifiez ces valeurs selon vos besoins

# Configuration de la base de données PostgreSQL
DB_CONFIG = {
    'host': 'opsserveur.postgres.database.azure.com',
    'database': 'airelles',
    'user': 'doadmin',
    'password': '1248163264Aa@',
    'port': 5432,
    'sslmode': 'require'
}

# Configuration Email
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email_from': 'enzoberbeche@gmail.com',
    'email_password': 'wnqu dihk cyww exao',
    'email_to': 'enzoberbeche@opsconseil.com'
}

# Configuration des chemins
PATHS = {
    'fec_directory': '/sftp/fecclient/Airelles/Fec',
    'log_file': '/home/adminenzo/airelles/fec_loader.log',
    'cron_log': '/home/adminenzo/airelles/cron.log'
}

# Configuration du traitement
PROCESSING = {
    'batch_size': 1000,  # Taille des lots pour execute_values
    'encoding': 'latin-1',  # Encodage des fichiers FEC
    'max_retries': 3  # Nombre de tentatives en cas d'erreur
}
