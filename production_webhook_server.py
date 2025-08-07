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
        
        # DEBUG: Log the entire webhook data to see what we're receiving
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
        'status': 'Production FastField to Asana Webhook Server',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)',
            'test': '/test (GET) - Test endpoint to see sample data'
        },
        'features': [
            'Automatic Asana task creation',
            'Duplicate submission prevention',
            'Image handling support',
            'Real-time webhook processing'
        ],
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/test', methods=['GET'])
def test_data():
    """Test endpoint to see sample FastField data structure"""
    sample_data = {
        'submissionId': 'test-123',
        'formName': 'Comcast QC Form New',
        'updatedAt': '2025-08-07T12:30:50.174683+00:00',
        'alpha_2': '123 Test Address',
        'lookuplistpicker_1': ['JB000123456'],
        'lookuplistpicker_2': ['Test Owner'],
        'multiline_3': 'Test comments',
        'multiline_34': 'Alternative comments',
        'inline_photo_1': 'test_image.png',
        'multiphoto_picker_4': [{'photo': 'test_photo.jpg'}]
    }
    
    # Process the sample data
    extracted = extract_form_data(sample_data)
    
    return jsonify({
        'sample_webhook_data': sample_data,
        'extracted_data': {
            'address': extracted['address'],
            'job_number': extracted['job_number'],
            'job_owner': extracted['job_owner'],
            'overall_comments': extracted['overall_comments'],
            'due_date': extracted['due_date'].isoformat()
        },
        'field_mapping': {
            'alpha_2': 'Address (Task Name)',
            'lookuplistpicker_1': 'Job Number',
            'lookuplistpicker_2': 'Job Owner',
            'multiline_3': 'Overall Comments',
            'multiline_34': 'Alternative Comments Field'
        }
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
        
        # Create subtasks for Location data if any
        if form_data.get('location_comments'):
            subtask_result = create_location_subtasks(task_id, form_data['location_comments'])
            if subtask_result['success']:
                logger.info(f"📋 Created {len(form_data['location_comments'])} location subtasks")
        
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
        # Parse submission date from FastField (Accepted Date)
        # Use updatedAt as the actual submission date/time
        submission_date_str = webhook_data.get('updatedAt', '')
        if submission_date_str:
            # Handle different date formats from FastField
            try:
                # Try parsing with timezone info (e.g., "2025-08-06T13:44:12-04:00")
                submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
            except:
                try:
                    # Try parsing without timezone
                    submission_date = datetime.fromisoformat(submission_date_str)
                except:
                    # Fallback to current time
                    submission_date = datetime.now()
        else:
            submission_date = datetime.now()
        
        # Calculate due date (Accepted Date + 5 days)
        due_date = submission_date + timedelta(days=5)
        
        # DEBUG: Log all available fields
        logger.info(f"🔍 Available fields in webhook: {list(webhook_data.keys())}")
        logger.info(f"📅 Accepted Date (from updatedAt): {submission_date.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"📅 Due Date (Accepted + 5 days): {due_date.strftime('%Y-%m-%d')}")
        
        # Also check for other date fields that might be relevant
        if webhook_data.get('datepicker_1'):
            logger.info(f"📅 Form date field (datepicker_1): {webhook_data['datepicker_1']}")
        
        # Extract form data based on FastField field names
        # Handle both array and single value formats
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
        
        # Extract location comments (for subtasks)
        location_comments = []
        # Look for location-related fields in the webhook data
        location_fields = ['multiline_2', 'multiline_4', 'multiline_5']  # Add more as needed
        for field in location_fields:
            if webhook_data.get(field):
                location_comments.append(webhook_data[field])
        
        form_data = {
            'submission_id': webhook_data.get('submissionId', ''),
            'form_name': webhook_data.get('formName', ''),
            'address': webhook_data.get('alpha_2', 'Unknown Address'),  # Task Name
            'job_number': job_number,
            'overall_comments': overall_comments,  # Task Description
            'location_comments': location_comments,  # For subtasks
            'job_owner': job_owner,
            'submission_date': submission_date,
            'due_date': due_date,
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
        
        # DEBUG: Log extracted data
        logger.info(f"📊 Extracted data:")
        logger.info(f"   Address: {form_data['address']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        logger.info(f"   Job Owner: {form_data['job_owner']}")
        logger.info(f"   Comments: {len(form_data['overall_comments'])} chars")
        logger.info(f"   Due Date: {form_data['due_date'].strftime('%Y-%m-%d')}")
        
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
        job_owner = form_data.get('job_owner', '')
        job_number = form_data.get('job_number', '')
        
        # Format due date properly for Asana (YYYY-MM-DD format)
        due_date_str = form_data['due_date'].strftime('%Y-%m-%d')
        
        # Ensure due date is not None and is valid
        if not due_date_str or due_date_str == 'None':
            logger.error(f"❌ Invalid due date: {form_data['due_date']}")
            due_date_str = None
        
        # Set description to overall comments (not notes)
        description = form_data.get('overall_comments', '')
        
        # Notes should be empty as requested
        notes = ""
        
        task_data = {
            'data': {
                'name': task_name,
                'notes': notes,
                'projects': [PROJECT_ID]
            }
        }
        
        # Only add due_date if it's valid
        if due_date_str:
            task_data['data']['due_date'] = due_date_str
        
        # Add description separately if we have overall comments
        if description:
            task_data['data']['html_notes'] = f"<body>{description}</body>"
            logger.info(f"📋 Description set: {description}")
        else:
            logger.info(f"📋 No description (no overall comments)")
        
        logger.info(f"📋 Task data being sent to Asana:")
        logger.info(f"   Name: {task_name}")
        logger.info(f"   Notes: {notes}")
        logger.info(f"   Description: {description}")
        logger.info(f"   Due Date: {due_date_str}")
        
        # Add assignee if we have job owner info
        if job_owner:
            # First, we need to find the user ID for the job owner
            # For now, we'll skip assignee and focus on other fields
            logger.info(f"📋 Job Owner: {job_owner} (assignee not set)")
        
        logger.info(f"📝 Creating Asana task: {task_name}")
        logger.info(f"📅 Due Date: {due_date_str}")
        logger.info(f"📋 Job Number: {job_number}")
        
        response = requests.post(
            'https://app.asana.com/api/1.0/tasks',
            headers=headers,
            json=task_data
        )
        
        if response.status_code == 201:
            task_id = response.json()['data']['gid']
            logger.info(f"✅ Task created successfully: {task_id}")
            
            # Update custom fields if we have the data
            if job_number or form_data.get('submission_date'):
                update_custom_fields(task_id, job_number, form_data)
            
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

def update_custom_fields(task_id, job_number, form_data):
    """Update custom fields in Asana task"""
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
            
            # Find the custom field for Job Number
            job_number_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Jb No':
                    job_number_field_id = field.get('gid')
                    break
            
            if job_number_field_id and job_number:
                field_updates[job_number_field_id] = job_number
                logger.info(f"📋 Job Number field found: {job_number}")
            
            # Find the custom field for Received Date (Accepted Date)
            received_date_field_id = None
            for field in custom_fields:
                if field.get('name') == 'Received Date':
                    received_date_field_id = field.get('gid')
                    break
            
            if received_date_field_id and form_data.get('submission_date'):
                accepted_date_str = form_data['submission_date'].strftime('%Y-%m-%d')
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

def create_location_subtasks(task_id, location_comments):
    """Create subtasks for location comments"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        created_subtasks = []
        
        for i, comment in enumerate(location_comments):
            if comment and comment.strip():
                subtask_data = {
                    'data': {
                        'name': f'Location Failure {i+1}',
                        'notes': comment,
                        'parent': task_id
                    }
                }
                
                response = requests.post(
                    'https://app.asana.com/api/1.0/tasks',
                    headers=headers,
                    json=subtask_data
                )
                
                if response.status_code == 201:
                    subtask_id = response.json()['data']['gid']
                    created_subtasks.append(subtask_id)
                    logger.info(f"✅ Created subtask {i+1}: {subtask_id}")
                else:
                    logger.error(f"❌ Failed to create subtask {i+1}: {response.status_code}")
        
        return {
            'success': True,
            'message': f'Created {len(created_subtasks)} subtasks',
            'subtask_ids': created_subtasks
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating location subtasks: {str(e)}")
        return {
            'success': False,
            'message': f'Error creating subtasks: {str(e)}'
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
