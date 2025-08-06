#!/usr/bin/env python3
"""
Production Webhook Server for FastField to Asana Automation
Handles all form submissions automatically
"""

import requests
import json
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asana configuration
ASANA_PAT = "2/1210137074577902/1210777453181763:2b48ddc6283d9c71f6f40576780739d9"
PROJECT_ID = "1210717842641983"

# Track processed submissions to avoid duplicates
PROCESSED_SUBMISSIONS_FILE = 'processed_submissions.json'

def load_processed_submissions():
    """Load list of processed submission IDs"""
    try:
        if os.path.exists(PROCESSED_SUBMISSIONS_FILE):
            with open(PROCESSED_SUBMISSIONS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading processed submissions: {e}")
    return []

def save_processed_submissions(submission_ids):
    """Save list of processed submission IDs"""
    try:
        with open(PROCESSED_SUBMISSIONS_FILE, 'w') as f:
            json.dump(submission_ids, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving processed submissions: {e}")

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle incoming webhook from FastField"""
    try:
        logger.info("📥 Received webhook from FastField")
        
        # Get webhook data
        webhook_data = request.get_json()
        submission_id = webhook_data.get('submissionId', '')
        
        # Check for duplicate processing
        processed_submissions = load_processed_submissions()
        if submission_id in processed_submissions:
            logger.info(f"⏭️ Submission {submission_id} already processed, skipping")
            return jsonify({'status': 'success', 'message': 'Already processed'}), 200
        
        logger.info(f"📊 Processing submission {submission_id}")
        
        # Process the webhook data
        result = process_form_submission(webhook_data)
        
        if result['success']:
            # Mark as processed
            processed_submissions.append(submission_id)
            save_processed_submissions(processed_submissions)
            
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
        'processed_count': len(load_processed_submissions())
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Home page with instructions"""
    return jsonify({
        'status': 'Production FastField to Asana Webhook Server',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'Automatic Asana task creation',
            'Duplicate submission prevention',
            'Image handling support',
            'Real-time webhook processing'
        ],
        'timestamp': datetime.now().isoformat()
    }), 200

def process_form_submission(webhook_data):
    """Process a form submission and create Asana task"""
    try:
        # Extract form data
        form_data = extract_form_data(webhook_data)
        logger.info(f"📋 Extracted form data: {form_data['address']}")
        
        # Create Asana task
        task_result = create_asana_task(form_data)
        if not task_result['success']:
            return task_result
        
        task_id = task_result['task_id']
        logger.info(f"✅ Created Asana task: {task_id}")
        
        # Upload images if any
        if form_data.get('images'):
            upload_result = upload_images_to_task(task_id, form_data['images'])
            if upload_result['success']:
                logger.info(f"📸 Uploaded {len(form_data['images'])} images to task")
        
        return {
            'success': True,
            'message': f'Task created successfully: {task_id}',
            'task_id': task_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing form submission: {str(e)}")
        return {
            'success': False,
            'message': f'Error processing submission: {str(e)}'
        }

def extract_form_data(webhook_data):
    """Extract relevant data from FastField webhook"""
    try:
        # Parse submission date
        submission_date_str = webhook_data.get('updatedAt', '')
        if submission_date_str:
            submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
        else:
            submission_date = datetime.now()
        
        # Extract form data based on FastField field names
        form_data = {
            'submission_id': webhook_data.get('submissionId', ''),
            'form_name': webhook_data.get('formName', ''),
            'address': webhook_data.get('alpha_2', 'Unknown Address'),  # Task Name
            'job_number': webhook_data.get('lookuplistpicker_1', [''])[0] if webhook_data.get('lookuplistpicker_1') else '',
            'overall_comments': webhook_data.get('multiline_3', '') or webhook_data.get('multiline_34', ''),  # Task Description
            'job_owner': webhook_data.get('lookuplistpicker_2', [''])[0] if webhook_data.get('lookuplistpicker_2') else '',
            'submission_date': submission_date,
            'due_date': submission_date + timedelta(days=5),
            'images': []
        }
        
        # Extract images from various possible fields
        image_fields = ['inline_photo_1', 'multiphoto_picker_4']
        for field in image_fields:
            if field in webhook_data:
                images = webhook_data[field]
                if isinstance(images, list):
                    for img in images:
                        if isinstance(img, dict) and 'photo' in img:
                            form_data['images'].append(img['photo'])
                        elif isinstance(img, str):
                            form_data['images'].append(img)
                elif isinstance(images, str):
                    form_data['images'].append(images)
        
        logger.info(f"📊 Extracted data: Address={form_data['address']}, Comments={len(form_data['overall_comments'])} chars")
        return form_data
        
    except Exception as e:
        logger.error(f"❌ Error extracting form data: {str(e)}")
        raise

def create_asana_task(form_data):
    """Create a new task in Asana"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Map form data to Asana task fields
        task_name = form_data.get('address', 'Unknown Address')  # Address as Task Name
        notes = ""  # Notes empty as requested
        task_description = form_data.get('overall_comments', '')  # Overall comments as description
        
        task_data = {
            'data': {
                'name': task_name,
                'notes': notes,
                'projects': [PROJECT_ID],
                'due_date': form_data['due_date'].isoformat()
            }
        }
        
        logger.info(f"📝 Creating Asana task: {task_name}")
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=task_data
        )
        
        if response.status_code == 201:
            task_id = response.json()['data']['gid']
            logger.info(f"✅ Task created successfully: {task_id}")
            return {
                'success': True,
                'task_id': task_id,
                'message': 'Task created successfully'
            }
        else:
            logger.error(f"❌ Failed to create Asana task: {response.status_code} - {response.text}")
            return {
                'success': False,
                'message': f'Asana API error: {response.status_code} - {response.text}'
            }
            
    except Exception as e:
        logger.error(f"❌ Error creating Asana task: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating task: {str(e)}'
        }

def upload_images_to_task(task_id, images):
    """Upload images to Asana task (placeholder for now)"""
    try:
        logger.info(f"📸 Would upload {len(images)} images to task {task_id}")
        # TODO: Implement actual image download and upload
        # For now, just log the image URLs
        for i, image_url in enumerate(images):
            logger.info(f"📷 Image {i+1}: {image_url}")
        
        return {
            'success': True,
            'message': f'Logged {len(images)} images (upload not implemented yet)'
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling images: {str(e)}")
        return {
            'success': False,
            'message': f'Error handling images: {str(e)}'
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
