#!/usr/bin/env python3
"""
Local Webhook Server for FastField to Asana
Receives webhooks directly on your machine and creates Asana tasks
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Asana Configuration
ASANA_PAT = "2/1210137074577902/1210777453181763:2b48ddc6283d9c71f6f40576780739d9"
PROJECT_ID = "1210717842641983"

app = Flask(__name__)

# Track processed submissions
processed_submissions = []

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle incoming webhook from FastField"""
    try:
        logger.info("📥 Received webhook from FastField")
        
        # Get webhook data
        webhook_data = request.get_json()
        submission_id = webhook_data.get('submissionId', '')
        
        # Check for duplicate processing
        if submission_id in processed_submissions:
            logger.info(f"⏭️ Submission {submission_id} already processed, skipping")
            return jsonify({'status': 'success', 'message': 'Already processed'}), 200
        
        logger.info(f"📊 Processing submission {submission_id}")
        
        # Create Asana task
        result = create_asana_task(webhook_data)
        
        if result['success']:
            # Mark as processed
            processed_submissions.append(submission_id)
            logger.info(f"✅ Successfully processed submission {submission_id}")
            return jsonify({'status': 'success', 'message': result['message']}), 200
        else:
            logger.error(f"❌ Failed to process submission {submission_id}: {result['message']}")
            return jsonify({'status': 'error', 'message': result['message']}), 400
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'processed_count': len(processed_submissions)
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Home page"""
    return jsonify({
        'status': 'Local FastField to Asana Webhook Server',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'Local webhook server',
            'No Heroku dependency',
            'Direct Asana task creation'
        ],
        'webhook_url': 'http://localhost:5000/webhook',
        'timestamp': datetime.now().isoformat()
    }), 200

def create_asana_task(webhook_data):
    """Create Asana task from webhook data"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Extract data from webhook
        form_data = webhook_data
        
        # Task name (address)
        task_name = form_data.get('alpha_2', 'Unknown Address')
        
        # Job number
        job_number = ''
        if form_data.get('lookuplistpicker_1'):
            if isinstance(form_data['lookuplistpicker_1'], dict):
                selected_values = form_data['lookuplistpicker_1'].get('selectedValues', [])
                job_number = selected_values[0] if selected_values else ''
            elif isinstance(form_data['lookuplistpicker_1'], list):
                job_number = form_data['lookuplistpicker_1'][0] if form_data['lookuplistpicker_1'] else ''
            else:
                job_number = form_data['lookuplistpicker_1']
        
        # Dates
        accepted_date = datetime.now()
        if form_data.get('datepicker_1'):
            try:
                accepted_date = datetime.fromisoformat(form_data['datepicker_1'].replace('Z', '+00:00'))
            except:
                try:
                    accepted_date = datetime.fromisoformat(form_data['datepicker_1'])
                except:
                    pass
        
        due_date = accepted_date + timedelta(days=5)
        
        logger.info(f"📋 Creating task: {task_name}")
        logger.info(f"   Job Number: {job_number}")
        logger.info(f"   Due Date: {due_date.strftime('%m/%d/%Y')}")
        
        # Create task
        task_data = {
            'data': {
                'name': task_name,
                'notes': '',
                'projects': [PROJECT_ID],
                'due_date': due_date.strftime('%m/%d/%Y')
            }
        }
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=task_data
        )
        
        if response.status_code == 201:
            task_id = response.json()['data']['gid']
            logger.info(f"✅ Task created: {task_id}")
            
            # Update custom fields
            update_custom_fields(task_id, job_number, accepted_date.strftime('%m/%d/%Y'))
            
            return {
                'success': True,
                'task_id': task_id,
                'message': f'Task created successfully: {task_id}'
            }
        else:
            logger.error(f"❌ Failed to create task: {response.status_code}")
            return {
                'success': False,
                'message': f'Asana API error: {response.status_code}'
            }
            
    except Exception as e:
        logger.error(f"❌ Error creating task: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating task: {str(e)}'
        }

def update_custom_fields(task_id, job_number, accepted_date):
    """Update custom fields in Asana task"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Get available custom fields
        response = requests.get(
            f'https://app.asana.com/api/1.0/tasks/{task_id}',
            headers=headers,
            params={'opt_fields': 'custom_fields'}
        )
        
        if response.status_code == 200:
            task_data = response.json()['data']
            custom_fields = task_data.get('custom_fields', [])
            
            # Prepare updates
            field_updates = {}
            
            # Update Job Number field
            for field in custom_fields:
                if field.get('name') == 'Jb No' and job_number:
                    field_updates[field.get('gid')] = job_number
                    logger.info(f"   ✅ Job Number: {job_number}")
                    break
            
            # Update Received Date field
            for field in custom_fields:
                if field.get('name') == 'Received Date' and accepted_date:
                    field_updates[field.get('gid')] = accepted_date
                    logger.info(f"   ✅ Received Date: {accepted_date}")
                    break
            
            # Apply updates
            if field_updates:
                update_data = {
                    'data': {
                        'custom_fields': field_updates
                    }
                }
                
                update_response = requests.put(
                    f'https://app.asana.com/api/1.0/tasks/{task_id}',
                    headers=headers,
                    json=update_data
                )
                
                if update_response.status_code == 200:
                    logger.info("   ✅ Custom fields updated successfully")
                else:
                    logger.error(f"   ❌ Failed to update custom fields: {update_response.status_code}")
        
    except Exception as e:
        logger.error(f"❌ Error updating custom fields: {str(e)}")

def start_server():
    """Start the local webhook server"""
    logger.info("🚀 STARTING LOCAL WEBHOOK SERVER")
    logger.info("=" * 50)
    logger.info("🌐 Server will be available at: http://localhost:5000")
    logger.info("📡 Webhook endpoint: http://localhost:5000/webhook")
    logger.info("📊 Health check: http://localhost:5000/health")
    logger.info("=" * 50)
    logger.info("💡 To make this accessible from the internet, use ngrok:")
    logger.info("   ngrok http 5000")
    logger.info("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    start_server()
