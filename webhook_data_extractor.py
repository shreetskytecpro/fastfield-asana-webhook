#!/usr/bin/env python3
"""
Webhook Data Extractor
Extract data from webhook URLs and create Asana tasks automatically
"""

import requests
import json
import time
import logging
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Asana Configuration
ASANA_PAT = "2/1210137074577902/1210777453181763:2b48ddc6283d9c71f6f40576780739d9"
PROJECT_ID = "1210717842641983"

# Track processed submissions
PROCESSED_FILE = 'processed_submissions.json'

def load_processed_submissions():
    """Load list of processed submission IDs"""
    try:
        if os.path.exists(PROCESSED_FILE):
            with open(PROCESSED_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading processed submissions: {e}")
    return []

def save_processed_submissions(submission_ids):
    """Save list of processed submission IDs"""
    try:
        with open(PROCESSED_FILE, 'w') as f:
            json.dump(submission_ids, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving processed submissions: {e}")

def get_webhook_data(webhook_url):
    """Get data from webhook URL"""
    try:
        logger.info(f"📡 Fetching data from: {webhook_url}")
        
        response = requests.get(webhook_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Successfully fetched webhook data")
            return data
        else:
            logger.error(f"❌ Failed to fetch webhook data: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error fetching webhook data: {str(e)}")
        return None

def extract_form_data(webhook_data):
    """Extract form data from webhook response"""
    try:
        # Handle different webhook response formats
        if isinstance(webhook_data, list):
            # Multiple submissions
            submissions = webhook_data
        elif isinstance(webhook_data, dict):
            # Single submission or response wrapper
            if 'submissions' in webhook_data:
                submissions = webhook_data['submissions']
            elif 'data' in webhook_data:
                submissions = [webhook_data['data']]
            else:
                submissions = [webhook_data]
        else:
            logger.error("❌ Unknown webhook data format")
            return []
        
        logger.info(f"📊 Found {len(submissions)} submissions")
        return submissions
        
    except Exception as e:
        logger.error(f"❌ Error extracting form data: {str(e)}")
        return []

def create_asana_task(submission_data):
    """Create Asana task from submission data"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Extract data from submission
        if isinstance(submission_data, dict):
            form_data = submission_data
        else:
            form_data = submission_data.get('formData', {})
        
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

def process_webhook_url(webhook_url):
    """Process webhook URL and create Asana tasks"""
    try:
        logger.info("🔄 PROCESSING WEBHOOK URL")
        
        # Get webhook data
        webhook_data = get_webhook_data(webhook_url)
        if not webhook_data:
            logger.error("❌ Failed to get webhook data")
            return
        
        # Extract form data
        submissions = extract_form_data(webhook_data)
        if not submissions:
            logger.info("📭 No submissions found in webhook data")
            return
        
        # Load processed submissions
        processed_submissions = load_processed_submissions()
        
        # Process new submissions
        new_count = 0
        for submission in submissions:
            submission_id = submission.get('submissionId', '')
            
            if submission_id and submission_id not in processed_submissions:
                logger.info(f"📊 Processing submission: {submission_id}")
                
                # Create Asana task
                result = create_asana_task(submission)
                
                if result['success']:
                    # Mark as processed
                    processed_submissions.append(submission_id)
                    new_count += 1
                    logger.info(f"✅ Successfully processed submission: {submission_id}")
                else:
                    logger.error(f"❌ Failed to process submission: {submission_id}")
        
        # Save processed submissions
        if new_count > 0:
            save_processed_submissions(processed_submissions)
            logger.info(f"🎉 Processed {new_count} new submissions")
        else:
            logger.info("📭 No new submissions to process")
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook URL: {str(e)}")

def run_automation():
    """Run the automation loop"""
    logger.info("🚀 STARTING WEBHOOK DATA EXTRACTOR")
    logger.info("=" * 60)
    
    # Get webhook URL from user
    print("\n📡 WEBHOOK DATA EXTRACTOR")
    print("=" * 50)
    print("Enter your webhook URL (e.g., https://webhook.site/...)")
    print("Or press Enter to use default Heroku URL")
    
    webhook_url = input("\nWebhook URL: ").strip()
    
    if not webhook_url:
        webhook_url = "https://fastfield-asana-webhook-e5e82c557bf4.herokuapp.com/webhook"
        logger.info(f"Using default URL: {webhook_url}")
    
    logger.info(f"🎯 Target webhook: {webhook_url}")
    
    while True:
        try:
            # Process webhook URL
            process_webhook_url(webhook_url)
            
            # Wait for next check (2 minutes)
            logger.info("⏰ Waiting 2 minutes before next check...")
            time.sleep(120)
            
        except KeyboardInterrupt:
            logger.info("🛑 Automation stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Error in automation loop: {str(e)}")
            logger.info("⏰ Waiting 1 minute before retry...")
            time.sleep(60)

if __name__ == '__main__':
    run_automation()
