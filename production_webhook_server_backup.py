#!/usr/bin/env python3
"""
FastField to Asana Data Storage & Transformer
Stores real webhook data and provides batch processing endpoint
VERSION: 2.0 - REAL DATA STORAGE
"""

import json
import logging
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# File to store submissions
SUBMISSIONS_FILE = 'stored_submissions.json'

def load_stored_submissions():
    """Load stored submissions from file"""
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading stored submissions: {e}")
    return []

def save_stored_submissions(submissions):
    """Save submissions to file"""
    try:
        with open(SUBMISSIONS_FILE, 'w') as f:
            json.dump(submissions, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving stored submissions: {e}")

def store_submission(webhook_data):
    """Store webhook submission data"""
    try:
        # Load existing submissions
        submissions = load_stored_submissions()
        
        # Add timestamp and processing status
        submission_data = {
            'submissionId': webhook_data.get('submissionId'),
            'stored_at': datetime.now().isoformat(),
            'processed': False,
            'raw_data': webhook_data
        }
        
        # Add to list
        submissions.append(submission_data)
        
        # Save back to file
        save_stored_submissions(submissions)
        
        logger.info(f"📦 Stored submission: {submission_data['submissionId']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error storing submission: {str(e)}")
        return False

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    submissions = load_stored_submissions()
    unprocessed_count = len([s for s in submissions if not s.get('processed', False)])
    
    return jsonify({
        'status': 'FastField Data Storage & Batch Processor v2.0',
        'endpoints': {
            'webhook': '/webhook (POST) - Store form submissions',
            'stored_data': '/stored_data (GET) - Get all stored submissions',
            'unprocessed_data': '/unprocessed_data (GET) - Get unprocessed submissions',
            'mark_processed': '/mark_processed (POST) - Mark submissions as processed',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'Real webhook data storage',
            'Batch processing support',
            'Processed tracking',
            'Data persistence',
            'REAL DATA STORAGE ENABLED v2.0'
        ],
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
        
        # Store the submission
        if store_submission(webhook_data):
            return jsonify({
                'message': 'Submission stored successfully',
                'submissionId': submission_id,
                'status': 'stored'
            }), 200
        else:
            return jsonify({
                'error': 'Failed to store submission',
                'submissionId': submission_id
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error in webhook handler: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stored_data', methods=['GET'])
def get_stored_data():
    """Get all stored submissions"""
    try:
        submissions = load_stored_submissions()
        
        return jsonify({
            'submissions': submissions,
            'count': len(submissions),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting stored data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/unprocessed_data', methods=['GET'])
def get_unprocessed_data():
    """Get only unprocessed submissions"""
    try:
        submissions = load_stored_submissions()
        unprocessed = [s for s in submissions if not s.get('processed', False)]
        
        return jsonify({
            'unprocessed_submissions': unprocessed,
            'count': len(unprocessed),
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
        
        # Load submissions
        submissions = load_stored_submissions()
        
        # Mark as processed
        updated_count = 0
        for submission in submissions:
            if submission.get('submissionId') in submission_ids:
                submission['processed'] = True
                submission['processed_at'] = datetime.now().isoformat()
                updated_count += 1
        
        # Save back
        save_stored_submissions(submissions)
        
        logger.info(f"✅ Marked {updated_count} submissions as processed")
        
        return jsonify({
            'message': f'Marked {updated_count} submissions as processed',
            'updated_count': updated_count
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error marking processed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    submissions = load_stored_submissions()
    
    return jsonify({
        'status': 'healthy',
        'service': 'FastField Data Storage v2.0',
        'total_submissions': len(submissions),
        'unprocessed_submissions': len([s for s in submissions if not s.get('processed', False)]),
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
