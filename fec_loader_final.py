#!/usr/bin/env python3
"""
Script final pour le chargement automatique des fichiers FEC
- Détection des modifications via hash
- Prévention des doublons
- Envoi d'email avec rapport
- Optimisé pour les performances
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import hashlib
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import logging
import sys

# Configuration
FEC_DIRECTORY = "/sftp/fecclient/Airelles/Fec"
DB_CONFIG = {
    'host': 'opsserveur.postgres.database.azure.com',
    'database': 'airelles',
    'user': 'doadmin',
    'password': '1248163264Aa@',
    'port': 5432,
    'sslmode': 'require'
}

# Configuration Email
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "enzoberbeche@gmail.com"
EMAIL_PASSWORD = "wnqu dihk cyww exao"
EMAIL_TO = "enzoberbeche@opsconseil.com"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/adminenzo/airelles/fec_loader.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FECLoader:
    def __init__(self):
        self.connection = None
        self.stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_modified': 0,
            'files_skipped': 0,
            'total_rows_loaded': 0,
            'errors': []
        }
    
    def connect_db(self):
        """Connexion à la base de données PostgreSQL"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("Connexion à la base de données réussie")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            self.stats['errors'].append(f"Connexion DB: {e}")
            return False
    
    def close_db(self):
        """Fermeture de la connexion à la base de données"""
        if self.connection:
            self.connection.close()
            logger.info("Connexion à la base de données fermée")
    
    def get_file_hash(self, file_path):
        """Calcule le hash MD5 d'un fichier"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Erreur lors du calcul du hash pour {file_path}: {e}")
            return None
    
    def get_file_modified_time(self, file_path):
        """Récupère la date de dernière modification d'un fichier"""
        try:
            return datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la date de modification pour {file_path}: {e}")
            return None
    
    def is_file_modified(self, file_name, current_hash, current_modified):
        """Vérifie si un fichier a été modifié depuis la dernière fois"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                SELECT last_hash, last_modified 
                FROM bronze.fec_file_status 
                WHERE file_name = %s
            """, (file_name,))
            
            result = cursor.fetchone()
            
            if not result:
                return True  # Fichier jamais traité
            
            last_hash, last_modified = result
            return last_hash != current_hash or last_modified != current_modified
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de modification pour {file_name}: {e}")
            return True
        finally:
            cursor.close()
    
    def load_fec_file(self, file_path, file_name):
        """Charge un fichier FEC dans la base de données"""
        logger.info(f"Chargement du fichier: {file_name}")
        
        try:
            # Lire le fichier
            df = pd.read_csv(file_path, sep='\t', encoding='latin-1', dtype=str)
            logger.info(f"  Fichier lu: {len(df)} lignes")
            
            # Ajouter les métadonnées
            file_hash = self.get_file_hash(file_path)
            file_modified = self.get_file_modified_time(file_path)
            
            # Nettoyer les noms de colonnes
            df.columns = df.columns.str.strip()
            
            # Définir les colonnes attendues (26 colonnes)
            expected_columns = [
                'journal_code', 'journal_lib', 'ecriture_num', 'ecriture_date', 'compte_num', 'compte_lib',
                'comp_aux_num', 'comp_aux_lib', 'piece_ref', 'piece_date', 'ecriture_lib', 'debit', 'credit',
                'ecriture_let', 'date_let', 'valid_date', 'montant_devise', 'idevise', 'code_etbt',
                'type_piece', 'edate', 'ref_origine', 'numero', 'numero_def', 'origine_lot', 'code_etbt2'
            ]
            
            # Gérer les fichiers avec 25 ou 26 colonnes
            num_cols = len(df.columns)
            logger.info(f"  Nombre de colonnes détecté: {num_cols}")
            
            if num_cols == 25:
                # Fichier avec 25 colonnes - ajouter une colonne vide pour code_etbt2
                df['code_etbt2'] = None
                df = df.iloc[:, :26]  # S'assurer qu'on a exactement 26 colonnes
            elif num_cols >= 26:
                # Fichier avec 26+ colonnes - prendre les 26 premières
                df = df.iloc[:, :26]
            else:
                # Fichier avec moins de 25 colonnes - ajouter des colonnes vides
                missing_cols = 26 - num_cols
                for i in range(missing_cols):
                    df[f'col_{num_cols + i}'] = None
                df = df.iloc[:, :26]
            
            # Renommer les colonnes
            df.columns = expected_columns
            
            # Ajouter les métadonnées
            df['file_name'] = file_name
            df['file_hash'] = file_hash
            df['file_modified'] = file_modified
            
            # Remplacer les valeurs vides par None
            df = df.replace('', None)
            
            cursor = self.connection.cursor()
            
            # Supprimer les anciennes données de ce fichier (prévention des doublons)
            cursor.execute("DELETE FROM bronze.fec_raw WHERE file_name = %s", (file_name,))
            logger.info(f"  Anciennes données supprimées pour {file_name}")
            
            # Préparer les données pour execute_values
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['file_name'], row['file_hash'], row['file_modified'],
                    row.get('journal_code'), row.get('journal_lib'), row.get('ecriture_num'),
                    row.get('ecriture_date'), row.get('compte_num'), row.get('compte_lib'),
                    row.get('comp_aux_num'), row.get('comp_aux_lib'), row.get('piece_ref'),
                    row.get('piece_date'), row.get('ecriture_lib'), row.get('debit'),
                    row.get('credit'), row.get('ecriture_let'), row.get('date_let'),
                    row.get('valid_date'), row.get('montant_devise'), row.get('idevise'),
                    row.get('code_etbt'), row.get('type_piece'), row.get('edate'),
                    row.get('ref_origine'), row.get('numero'), row.get('numero_def'),
                    row.get('origine_lot'), row.get('code_etbt2')
                ))
            
            # Insérer avec execute_values (optimisé)
            execute_values(
                cursor,
                """
                INSERT INTO bronze.fec_raw (
                    file_name, file_hash, file_modified, journal_code, journal_lib,
                    ecriture_num, ecriture_date, compte_num, compte_lib, comp_aux_num,
                    comp_aux_lib, piece_ref, piece_date, ecriture_lib, debit, credit,
                    ecriture_let, date_let, valid_date, montant_devise, idevise,
                    code_etbt, type_piece, edate, ref_origine, numero, numero_def,
                    origine_lot, code_etbt2
                ) VALUES %s
                """,
                data,
                template=None,
                page_size=1000
            )
            
            # Mettre à jour le statut du fichier
            cursor.execute("""
                INSERT INTO bronze.fec_file_status (file_name, file_path, last_hash, last_modified, last_loaded, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (file_name) 
                DO UPDATE SET 
                    last_hash = EXCLUDED.last_hash,
                    last_modified = EXCLUDED.last_modified,
                    last_loaded = EXCLUDED.last_loaded,
                    status = EXCLUDED.status,
                    error_message = NULL
            """, (
                file_name, str(file_path), file_hash, file_modified,
                datetime.now(), 'loaded'
            ))
            
            self.connection.commit()
            logger.info(f"  ✓ {len(data)} lignes chargées avec succès")
            
            self.stats['total_rows_loaded'] += len(data)
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier {file_name}: {e}")
            self.stats['errors'].append(f"{file_name}: {e}")
            
            # Mettre à jour le statut d'erreur
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO bronze.fec_file_status (file_name, file_path, status, error_message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (file_name) 
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message
            """, (file_name, str(file_path), 'error', str(e)))
            self.connection.commit()
            return False
        finally:
            if 'cursor' in locals():
                cursor.close()
    
    def process_fec_files(self):
        """Traite tous les fichiers FEC du répertoire"""
        if not self.connect_db():
            return False
        
        try:
            fec_directory = Path(FEC_DIRECTORY)
            if not fec_directory.exists():
                logger.error(f"Le répertoire {FEC_DIRECTORY} n'existe pas")
                self.stats['errors'].append(f"Répertoire {FEC_DIRECTORY} introuvable")
                return False
            
            # Lister tous les fichiers .txt dans le répertoire
            fec_files = list(fec_directory.glob("*.txt"))
            
            if not fec_files:
                logger.warning(f"Aucun fichier .txt trouvé dans {FEC_DIRECTORY}")
                return True
            
            logger.info(f"Trouvé {len(fec_files)} fichiers FEC à traiter")
            
            for file_path in fec_files:
                file_name = file_path.name
                self.stats['files_processed'] += 1
                
                logger.info(f"Traitement du fichier: {file_name}")
                
                # Calculer le hash et la date de modification
                current_hash = self.get_file_hash(file_path)
                current_modified = self.get_file_modified_time(file_path)
                
                if not current_hash or not current_modified:
                    logger.error(f"Impossible de lire les métadonnées du fichier {file_name}")
                    self.stats['errors'].append(f"{file_name}: Impossible de lire les métadonnées")
                    continue
                
                # Vérifier si le fichier a été modifié
                if self.is_file_modified(file_name, current_hash, current_modified):
                    logger.info(f"  Fichier {file_name} modifié, chargement en cours...")
                    if self.load_fec_file(file_path, file_name):
                        self.stats['files_modified'] += 1
                    else:
                        self.stats['files_skipped'] += 1
                else:
                    logger.info(f"  Fichier {file_name} inchangé, ignoré")
                    self.stats['files_skipped'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement des fichiers FEC: {e}")
            self.stats['errors'].append(f"Erreur générale: {e}")
            return False
        finally:
            self.close_db()
    
    def send_email_report(self):
        """Envoie un rapport par email"""
        try:
            end_time = datetime.now()
            duration = end_time - self.stats['start_time']
            
            # Créer le contenu de l'email
            subject = f"Rapport FEC Loader - {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            html_content = f"""
            <html>
            <body>
                <h2>Rapport de chargement des fichiers FEC</h2>
                <p><strong>Date/Heure:</strong> {end_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Durée:</strong> {duration}</p>
                
                <h3>Statistiques</h3>
                <ul>
                    <li><strong>Fichiers traités:</strong> {self.stats['files_processed']}</li>
                    <li><strong>Fichiers modifiés:</strong> {self.stats['files_modified']}</li>
                    <li><strong>Fichiers ignorés:</strong> {self.stats['files_skipped']}</li>
                    <li><strong>Lignes chargées:</strong> {self.stats['total_rows_loaded']:,}</li>
                </ul>
                
                <h3>Erreurs</h3>
                {f"<ul>{''.join([f'<li>{error}</li>' for error in self.stats['errors']])}</ul>" if self.stats['errors'] else "<p>Aucune erreur</p>"}
                
                <p><em>Rapport généré automatiquement par FEC Loader</em></p>
            </body>
            </html>
            """
            
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_TO
            msg['Subject'] = subject
            
            # Ajouter le contenu HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Envoyer l'email
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            logger.info("Rapport envoyé par email avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False

def main():
    """Fonction principale"""
    logger.info("=== Démarrage du chargement des fichiers FEC ===")
    
    loader = FECLoader()
    success = loader.process_fec_files()
    
    # Envoyer le rapport par email
    loader.send_email_report()
    
    if success:
        logger.info("Chargement terminé avec succès")
        sys.exit(0)
    else:
        logger.error("Erreur lors du chargement")
        sys.exit(1)

if __name__ == "__main__":
    main()
