#!/usr/bin/env python3
"""
FastField to Asana Data Storage & Transformer
Stores real webhook data in PostgreSQL database and provides batch processing endpoint
VERSION: 3.0 - POSTGRESQL STORAGE - DEPLOYED
"""

import json
import logging
import os
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    try:
        if DATABASE_URL:
            # Parse the DATABASE_URL for PostgreSQL
            url = urlparse(DATABASE_URL)
            conn = psycopg2.connect(
                database=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port
            )
            return conn
        else:
            # Fallback to local SQLite for development
            import sqlite3
            conn = sqlite3.connect('submissions.db')
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        if DATABASE_URL:
            # PostgreSQL
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id SERIAL PRIMARY KEY,
                    submission_id VARCHAR(255) UNIQUE NOT NULL,
                    raw_data JSONB NOT NULL,
                    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    processed_at TIMESTAMP NULL
                )
            ''')
        else:
            # SQLite fallback
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id TEXT UNIQUE NOT NULL,
                    raw_data TEXT NOT NULL,
                    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE,
                    processed_at TIMESTAMP NULL
                )
            ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        return False

def store_submission_db(webhook_data):
    """Store webhook submission data in database"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        submission_id = webhook_data.get('submissionId')
        raw_data_json = json.dumps(webhook_data)
        
        cursor = conn.cursor()
        
        if DATABASE_URL:
            # PostgreSQL
            cursor.execute('''
                INSERT INTO submissions (submission_id, raw_data, stored_at, processed)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (submission_id) DO NOTHING
            ''', (submission_id, raw_data_json, datetime.now(), False))
        else:
            # SQLite
            cursor.execute('''
                INSERT OR IGNORE INTO submissions (submission_id, raw_data, stored_at, processed)
                VALUES (?, ?, ?, ?)
            ''', (submission_id, raw_data_json, datetime.now(), False))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📦 Stored submission in database: {submission_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error storing submission in database: {str(e)}")
        return False

def load_submissions_from_db(processed_only=False):
    """Load submissions from database"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
            
        cursor = conn.cursor()
        
        if processed_only:
            query = "SELECT * FROM submissions WHERE processed = %s" if DATABASE_URL else "SELECT * FROM submissions WHERE processed = ?"
            cursor.execute(query, (True,))
        else:
            cursor.execute("SELECT * FROM submissions")
        
        rows = cursor.fetchall()
        conn.close()
        
        submissions = []
        for row in rows:
            if DATABASE_URL:
                # PostgreSQL
                submission = {
                    'id': row[0],
                    'submissionId': row[1],
                    'raw_data': row[2] if isinstance(row[2], dict) else json.loads(row[2]),
                    'stored_at': row[3].isoformat() if row[3] else None,
                    'processed': row[4],
                    'processed_at': row[5].isoformat() if row[5] else None
                }
            else:
                # SQLite
                submission = {
                    'id': row['id'],
                    'submissionId': row['submission_id'],
                    'raw_data': json.loads(row['raw_data']),
                    'stored_at': row['stored_at'],
                    'processed': bool(row['processed']),
                    'processed_at': row['processed_at']
                }
            
            submissions.append(submission)
        
        return submissions
        
    except Exception as e:
        logger.error(f"❌ Error loading submissions from database: {str(e)}")
        return []

def mark_submissions_processed_db(submission_ids):
    """Mark submissions as processed in database"""
    try:
        conn = get_db_connection()
        if not conn:
            return 0
            
        cursor = conn.cursor()
        updated_count = 0
        
        for submission_id in submission_ids:
            if DATABASE_URL:
                # PostgreSQL
                cursor.execute('''
                    UPDATE submissions 
                    SET processed = %s, processed_at = %s 
                    WHERE submission_id = %s
                ''', (True, datetime.now(), submission_id))
            else:
                # SQLite
                cursor.execute('''
                    UPDATE submissions 
                    SET processed = ?, processed_at = ? 
                    WHERE submission_id = ?
                ''', (True, datetime.now(), submission_id))
            
            updated_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return updated_count
        
    except Exception as e:
        logger.error(f"❌ Error marking submissions as processed: {str(e)}")
        return 0

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    submissions = load_submissions_from_db()
    unprocessed_count = len([s for s in submissions if not s.get('processed', False)])
    
    return jsonify({
        'status': 'FastField PostgreSQL Storage v3.0 - DEPLOYED',
        'endpoints': {
            'webhook': '/webhook (POST) - Store form submissions',
            'stored_data': '/stored_data (GET) - Get all stored submissions',
            'unprocessed_data': '/unprocessed_data (GET) - Get unprocessed submissions',
            'mark_processed': '/mark_processed (POST) - Mark submissions as processed',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'PostgreSQL database storage',
            'Permanent data persistence',
            'Batch processing support', 
            'Processed tracking',
            'POSTGRESQL STORAGE v3.0 DEPLOYED'
        ],
        'database': {
            'type': 'PostgreSQL' if DATABASE_URL else 'SQLite (local)',
            'status': 'connected' if get_db_connection() else 'disconnected',
            'url_exists': bool(DATABASE_URL)
        },
        'stats': {
            'total_submissions': len(submissions),
            'unprocessed_submissions': unprocessed_count
        },
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle FastField webhook and store data"""
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.warning("⚠️ No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
        
        submission_id = webhook_data.get('submissionId')
        logger.info(f"📥 Received webhook for submission: {submission_id}")
        
        # Store the submission in database
        if store_submission_db(webhook_data):
            return jsonify({
                'message': 'Submission stored successfully in PostgreSQL database',
                'submissionId': submission_id,
                'status': 'stored',
                'storage': 'PostgreSQL' if DATABASE_URL else 'SQLite'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to store submission in database',
                'submissionId': submission_id
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error in webhook handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stored_data', methods=['GET'])
def get_stored_data():
    """Get all stored submissions"""
    try:
        submissions = load_submissions_from_db()
        
        return jsonify({
            'submissions': submissions,
            'count': len(submissions),
            'storage': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting stored data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/unprocessed_data', methods=['GET'])
def get_unprocessed_data():
    """Get only unprocessed submissions"""
    try:
        submissions = load_submissions_from_db()
        unprocessed = [s for s in submissions if not s.get('processed', False)]
        
        return jsonify({
            'unprocessed_submissions': unprocessed,
            'count': len(unprocessed),
            'storage': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting unprocessed data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mark_processed', methods=['POST'])
def mark_processed():
    """Mark submissions as processed"""
    try:
        request_data = request.get_json()
        submission_ids = request_data.get('submission_ids', [])
        
        if not submission_ids:
            return jsonify({'error': 'No submission IDs provided'}), 400
        
        # Mark as processed in database
        updated_count = mark_submissions_processed_db(submission_ids)
        
        logger.info(f"✅ Marked {updated_count} submissions as processed in database")
        
        return jsonify({
            'message': f'Marked {updated_count} submissions as processed',
            'updated_count': updated_count,
            'storage': 'PostgreSQL' if DATABASE_URL else 'SQLite'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error marking processed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    submissions = load_submissions_from_db()
    
    return jsonify({
        'status': 'healthy',
        'service': 'FastField PostgreSQL Storage v3.0',
        'database': {
            'type': 'PostgreSQL' if DATABASE_URL else 'SQLite',
            'connected': get_db_connection() is not None,
            'url_exists': bool(DATABASE_URL)
        },
        'total_submissions': len(submissions),
        'unprocessed_submissions': len([s for s in submissions if not s.get('processed', False)]),
        'timestamp': datetime.now().isoformat()
    }), 200

# Initialize database on startup
init_database()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
