#!/usr/bin/env python3
"""
DEBUG FastField to Asana Webhook Server
Add extensive logging to see what's happening
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
        'status': 'DEBUG FastField to Asana Webhook Server',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'features': [
            'Debug logging for troubleshooting',
            'Custom field update debugging',
            'Exact field mapping'
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
        
        # Create subtask if we have subtask data
        if form_data.get('subtask_name') and form_data.get('subtask_assignee'):
            subtask_result = create_subtask(task_id, form_data)
            if subtask_result['success']:
                logger.info(f" Created subtask: {form_data['subtask_name']}")
        
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
    """Extract relevant data from FastField webhook - DEBUG VERSION"""
    try:
        # 1. alpha_2 -> Name in Asana
        address = webhook_data.get('alpha_2', 'Unknown Address')
        logger.info(f" DEBUG: alpha_2 = {address}")
        
        # 2. lookuplistpicker_1 -> Jb No
        job_number = ''
        if webhook_data.get('lookuplistpicker_1'):
            logger.info(f"🔍 DEBUG: lookuplistpicker_1 = {webhook_data['lookuplistpicker_1']}")
            if isinstance(webhook_data['lookuplistpicker_1'], dict):
                # Handle the new structure with selectedValues
                selected_values = webhook_data['lookuplistpicker_1'].get('selectedValues', [])
                job_number = selected_values[0] if selected_values else ''
                logger.info(f"🔍 DEBUG: selectedValues = {selected_values}, job_number = {job_number}")
            elif isinstance(webhook_data['lookuplistpicker_1'], list):
                job_number = webhook_data['lookuplistpicker_1'][0] if webhook_data['lookuplistpicker_1'] else ''
                logger.info(f" DEBUG: list format, job_number = {job_number}")
            else:
                job_number = webhook_data['lookuplistpicker_1']
                logger.info(f"🔍 DEBUG: direct format, job_number = {job_number}")
        
        # 3. lookuplistpicker_2 -> Assignee for Sub Task
        subtask_assignee = ''
        if webhook_data.get('lookuplistpicker_2'):
            logger.info(f"🔍 DEBUG: lookuplistpicker_2 = {webhook_data['lookuplistpicker_2']}")
            if isinstance(webhook_data['lookuplistpicker_2'], dict):
                selected_names = webhook_data['lookuplistpicker_2'].get('selectedNames', [])
                subtask_assignee = selected_names[0] if selected_names else ''
                logger.info(f"🔍 DEBUG: selectedNames = {selected_names}, subtask_assignee = {subtask_assignee}")
            elif isinstance(webhook_data['lookuplistpicker_2'], list):
                subtask_assignee = webhook_data['lookuplistpicker_2'][0] if webhook_data['lookuplistpicker_2'] else ''
                logger.info(f" DEBUG: list format, subtask_assignee = {subtask_assignee}")
            else:
                subtask_assignee = webhook_data['lookuplistpicker_2']
                logger.info(f"🔍 DEBUG: direct format, subtask_assignee = {subtask_assignee}")
        
        # 4. listpicker_4 -> Name of the Sub Task
        subtask_name = ''
        if webhook_data.get('listpicker_4'):
            logger.info(f" DEBUG: listpicker_4 = {webhook_data['listpicker_4']}")
            if isinstance(webhook_data['listpicker_4'], dict):
                selected_names = webhook_data['listpicker_4'].get('selectedNames', [])
                subtask_name = selected_names[0] if selected_names else ''
                logger.info(f"🔍 DEBUG: selectedNames = {selected_names}, subtask_name = {subtask_name}")
            elif isinstance(webhook_data['listpicker_4'], list):
                subtask_name = webhook_data['listpicker_4'][0] if webhook_data['listpicker_4'] else ''
                logger.info(f" DEBUG: list format, subtask_name = {subtask_name}")
            else:
                subtask_name = webhook_data['listpicker_4']
                logger.info(f"🔍 DEBUG: direct format, subtask_name = {subtask_name}")
        
        # 5. datepicker_1 -> Accepted Date (and Due Date = Accepted + 5 days)
        accepted_date = None
        if webhook_data.get('datepicker_1'):
            logger.info(f" DEBUG: datepicker_1 = {webhook_data['datepicker_1']}")
            try:
                accepted_date = datetime.fromisoformat(webhook_data['datepicker_1'].replace('Z', '+00:00'))
                logger.info(f"🔍 DEBUG: parsed accepted_date = {accepted_date}")
            except:
                try:
                    accepted_date = datetime.fromisoformat(webhook_data['datepicker_1'])
                    logger.info(f"🔍 DEBUG: parsed accepted_date = {accepted_date}")
                except:
                    accepted_date = datetime.now()
                    logger.info(f"🔍 DEBUG: fallback accepted_date = {accepted_date}")
        else:
            accepted_date = datetime.now()
            logger.info(f"🔍 DEBUG: no datepicker_1, using now = {accepted_date}")
        
        due_date = accepted_date + timedelta(days=5)
        logger.info(f"🔍 DEBUG: calculated due_date = {due_date}")
        
        # 6. textlabel_2 -> Assignee of the overall task
        task_assignee = webhook_data.get('textlabel_2', '')
        logger.info(f" DEBUG: textlabel_2 = {task_assignee}")
        
        form_data = {
            'address': address,
            'job_number': job_number,
            'subtask_assignee': subtask_assignee,
            'subtask_name': subtask_name,
            'accepted_date': accepted_date,
            'due_date': due_date,
            'task_assignee': task_assignee
        }
        
        # DEBUG: Log extracted data
        logger.info(f"📊 FINAL EXTRACTED DATA:")
        logger.info(f"   Address (Name): {form_data['address']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        logger.info(f"   Sub Task Assignee: {form_data['subtask_assignee']}")
        logger.info(f"   Sub Task Name: {form_data['subtask_name']}")
        logger.info(f"   Accepted Date: {form_data['accepted_date'].strftime('%m/%d/%Y')}")
        logger.info(f"   Due Date: {form_data['due_date'].strftime('%m/%d/%Y')}")
        logger.info(f"   Task Assignee: {form_data['task_assignee']}")
        
        return form_data
        
    except Exception as e:
        logger.error(f"❌ Error extracting form data: {str(e)}")
        raise

def create_asana_task(form_data):
    """Create a new task in Asana - DEBUG VERSION"""
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
                'notes': '',  # Empty notes as requested
                'projects': [PROJECT_ID],
                'due_date': due_date_str
            }
        }
        
        logger.info(f"📋 TASK DATA BEING SENT TO ASANA:")
        logger.info(f"   Name: {form_data['address']}")
        logger.info(f"   Due Date: {due_date_str}")
        logger.info(f"   Task Assignee: {form_data['task_assignee']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        logger.info(f"   Accepted Date: {form_data['accepted_date'].strftime('%m/%d/%Y')}")
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=task_data
        )
        
        if response.status_code == 201:
            task_id = response.json()['data']['gid']
            logger.info(f"✅ Task created successfully: {task_id}")
            
            # Update custom fields
            if form_data['job_number'] or form_data['accepted_date']:
                logger.info(f"🔧 Updating custom fields for task {task_id}")
                update_custom_fields(task_id, form_data)
            else:
                logger.info(f"⚠️ No custom fields to update")
            
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

def create_subtask(task_id, form_data):
    """Create subtask with assignee"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        subtask_data = {
            'data': {
                'name': form_data['subtask_name'],
                'notes': f"Assignee: {form_data['subtask_assignee']}",
                'parent': task_id
            }
        }
        
        logger.info(f"📋 Creating subtask: {form_data['subtask_name']}")
        logger.info(f"   Assignee: {form_data['subtask_assignee']}")
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=subtask_data
        )
        
        if response.status_code == 201:
            subtask_id = response.json()['data']['gid']
            logger.info(f"✅ Created subtask: {subtask_id}")
            return {
                'success': True,
                'subtask_id': subtask_id,
                'message': 'Subtask created successfully'
            }
        else:
            logger.error(f"❌ Failed to create subtask: {response.status_code}")
            return {
                'success': False,
                'message': f'Failed to create subtask: {response.status_code}'
            }
            
    except Exception as e:
        logger.error(f"❌ Error creating subtask: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating subtask: {str(e)}'
        }

def update_custom_fields(task_id, form_data):
    """Update custom fields in Asana task - DEBUG VERSION"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"🔧 Getting custom fields for task {task_id}")
        
        # Get the task to see available custom fields
        response = requests.get(
            f'https://app.asana.com/api/1.0/tasks/{task_id}',
            headers=headers,
            params={'opt_fields': 'custom_fields'}
        )
        
        if response.status_code == 200:
            task_data = response.json()['data']
            custom_fields = task_data.get('custom_fields', [])
            
            logger.info(f"🔧 Found {len(custom_fields)} custom fields:")
            for field in custom_fields:
                logger.info(f"   - {field.get('name')}: {field.get('gid')}")
            
            # Prepare custom field updates
            field_updates = {}
            
            # Find the Job Number field
            job_number_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Jb No':
                    job_number_field_id = field.get('gid')
                    logger.info(f" Found Jb No field: {job_number_field_id}")
                    break
            
            if job_number_field_id and form_data['job_number']:
                field_updates[job_number_field_id] = form_data['job_number']
                logger.info(f"📋 Job Number field found: {form_data['job_number']}")
            else:
                logger.info(f"⚠️ Job Number field not found or empty")
            
            # Find the Received Date field (Accepted Date)
            received_date_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Received Date':
                    received_date_field_id = field.get('gid')
                    logger.info(f"🔧 Found Received Date field: {received_date_field_id}")
                    break
            
            if received_date_field_id and form_data.get('accepted_date'):
                accepted_date_str = form_data['accepted_date'].strftime('%m/%d/%Y')
                field_updates[received_date_field_id] = accepted_date_str
                logger.info(f"📅 Accepted Date field found: {accepted_date_str}")
            else:
                logger.info(f"⚠️ Received Date field not found or no accepted_date")
            
            # Update all custom fields at once
            if field_updates:
                update_data = {
                    'data': {
                        'custom_fields': field_updates
                    }
                }
                
                logger.info(f"🔧 Updating custom fields: {field_updates}")
                
                update_response = requests.put(
                    f'https://app.asana.com/api/1.0/tasks/{task_id}',
                    headers=headers,
                    json=update_data
                )
                
                if update_response.status_code == 200:
                    logger.info(f"✅ Updated custom fields successfully")
                else:
                    logger.error(f"❌ Failed to update custom fields: {update_response.status_code} - {update_response.text}")
            else:
                logger.warning("⚠️ No custom fields to update")
        
    except Exception as e:
        logger.error(f"❌ Error updating custom fields: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)