#!/usr/bin/env python3
"""
SIMPLE FastField to Asana Webhook Server
Focus on basics: Name, Description, Due Date, Job Number, Accepted Date, Assignee
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
        
        # DEBUG: Log the entire webhook data
        logger.info(f"🔍 DEBUG: Full webhook data: {json.dumps(webhook_data, indent=2)}")
        
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
        'status': 'SIMPLE FastField to Asana Webhook Server',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'Simple Asana task creation',
            'Duplicate submission prevention',
            'Basic field mapping'
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
    """Extract relevant data from FastField webhook - SIMPLE VERSION"""
    try:
        # Parse submission date from FastField
        submission_date_str = webhook_data.get('updatedAt', '')
        if submission_date_str:
            try:
                submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
            except:
                try:
                    submission_date = datetime.fromisoformat(submission_date_str)
                except:
                    submission_date = datetime.now()
        else:
            submission_date = datetime.now()
        
        # Calculate due date (submission date + 5 days)
        due_date = submission_date + timedelta(days=5)
        
        # Extract basic fields
        job_number = ''
        if webhook_data.get('lookuplistpicker_1'):
            if isinstance(webhook_data['lookuplistpicker_1'], list):
                job_number = webhook_data['lookuplistpicker_1'][0] if webhook_data['lookuplistpicker_1'] else ''
            else:
                job_number = webhook_data['lookuplistpicker_1']
        
        job_owner = ''
        if webhook_data.get('lookuplistpicker_2'):
            if isinstance(webhook_data['lookuplistpicker_2'], list):
                job_owner = webhook_data['lookuplistpicker_2'][0] if webhook_data['lookuplistpicker_2'] else ''
            else:
                job_owner = webhook_data['lookuplistpicker_2']
        
        overall_comments = ''
        if webhook_data.get('multiline_3'):
            overall_comments = webhook_data['multiline_3']
        elif webhook_data.get('multiline_34'):
            overall_comments = webhook_data['multiline_34']
        
        form_data = {
            'address': webhook_data.get('alpha_2', 'Unknown Address'),
            'job_number': job_number,
            'job_owner': job_owner,
            'overall_comments': overall_comments,
            'submission_date': submission_date,
            'due_date': due_date
        }
        
        # DEBUG: Log extracted data
        logger.info(f" Extracted data:")
        logger.info(f"   Address: {form_data['address']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        logger.info(f"   Job Owner: {form_data['job_owner']}")
        logger.info(f"   Comments: {len(form_data['overall_comments'])} chars")
        logger.info(f"   Submission Date: {form_data['submission_date'].strftime('%m/%d/%Y')}")
        logger.info(f"   Due Date: {form_data['due_date'].strftime('%m/%d/%Y')}")
        
        return form_data
        
    except Exception as e:
        logger.error(f"❌ Error extracting form data: {str(e)}")
        raise

def create_asana_task(form_data):
    """Create a new task in Asana - SIMPLE VERSION"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Format due date as MM/DD/YYYY for Asana
        due_date_str = form_data['due_date'].strftime('%m/%d/%Y')
        
        # Create task with basic fields
        task_data = {
            'data': {
                'name': form_data['address'],
                'notes': form_data['overall_comments'],
                'projects': [PROJECT_ID],
                'due_date': due_date_str
            }
        }
        
        logger.info(f"📋 Task data being sent to Asana:")
        logger.info(f"   Name: {form_data['address']}")
        logger.info(f"   Notes: {form_data['overall_comments']}")
        logger.info(f"   Due Date: {due_date_str}")
        logger.info(f"   Job Owner: {form_data['job_owner']}")
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=task_data
        )
        
        if response.status_code == 201:
            task_id = response.json()['data']['gid']
            logger.info(f"✅ Task created successfully: {task_id}")
            
            # Update custom fields
            if form_data['job_number'] or form_data['submission_date']:
                update_custom_fields(task_id, form_data)
            
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

def update_custom_fields(task_id, form_data):
    """Update custom fields in Asana task - SIMPLE VERSION"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Get the task to see available custom fields
        response = requests.get(
            f'https://app.asana.com/api/1.0/tasks/{task_id}',
            headers=headers,
            params={'opt_fields': 'custom_fields'}
        )
        
        if response.status_code == 200:
            task_data = response.json()['data']
            custom_fields = task_data.get('custom_fields', [])
            
            # Prepare custom field updates
            field_updates = {}
            
            # Find the Job Number field
            job_number_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Jb No':
                    job_number_field_id = field.get('gid')
                    break
            
            if job_number_field_id and form_data['job_number']:
                field_updates[job_number_field_id] = form_data['job_number']
                logger.info(f"📋 Job Number field found: {form_data['job_number']}")
            
            # Find the Received Date field (Accepted Date)
            received_date_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Received Date':
                    received_date_field_id = field.get('gid')
                    break
            
            if received_date_field_id and form_data.get('submission_date'):
                accepted_date_str = form_data['submission_date'].strftime('%m/%d/%Y')
                field_updates[received_date_field_id] = accepted_date_str
                logger.info(f"📅 Accepted Date field found: {accepted_date_str}")
            
            # Update all custom fields at once
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
                    logger.info(f"✅ Updated custom fields successfully")
                else:
                    logger.error(f"❌ Failed to update custom fields: {update_response.status_code}")
            else:
                logger.warning("⚠️ No custom fields to update")
        
    except Exception as e:
        logger.error(f"❌ Error updating custom fields: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)