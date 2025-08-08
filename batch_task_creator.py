#!/usr/bin/env python3
"""
Batch Task Creator
Extract stored form data and create all Asana tasks at once
"""

import requests
import json
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

def get_stored_submissions():
    """Get stored submissions from Heroku or local storage"""
    try:
        # Option 1: Get from Heroku health endpoint
        heroku_url = "https://fastfield-asana-webhook-e5e82c557bf4.herokuapp.com/health"
        response = requests.get(heroku_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            processed_count = data.get('processed_count', 0)
            logger.info(f"📊 Found {processed_count} processed submissions on Heroku")
            
            # For now, we'll simulate stored data
            # In a real implementation, Heroku would store this in a database
            return get_simulated_stored_data()
        else:
            logger.error(f"❌ Failed to get Heroku data: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error getting stored submissions: {str(e)}")
        return []

def get_simulated_stored_data():
    """Simulate stored form data (replace with actual Heroku database query)"""
    # This would come from Heroku's database in a real implementation
    stored_submissions = [
        {
            "submissionId": "test-001",
            "alpha_2": "123 Main Street, City, State 12345",
            "lookuplistpicker_1": {"selectedValues": ["JB000123456"]},
            "datepicker_1": "2025-08-07T00:00:00-04:00",
            "textlabel_2": "john@company.com",
            "listpicker_4": {"selectedNames": ["Aerial Construction"]},
            "lookuplistpicker_2": {"selectedNames": ["Test Skytec (Internal)"]}
        },
        {
            "submissionId": "test-002", 
            "alpha_2": "456 Oak Avenue, Town, State 67890",
            "lookuplistpicker_1": {"selectedValues": ["JB000789012"]},
            "datepicker_1": "2025-08-07T00:00:00-04:00",
            "textlabel_2": "jane@company.com",
            "listpicker_4": {"selectedNames": ["Underground"]},
            "lookuplistpicker_2": {"selectedNames": ["Test Skytec (Internal)"]}
        }
    ]
    
    logger.info(f"📄 Loaded {len(stored_submissions)} stored submissions")
    return stored_submissions

def create_asana_task(submission_data):
    """Create Asana task from submission data"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        # Extract data from submission
        form_data = submission_data
        
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

def process_batch_submissions():
    """Process all stored submissions and create Asana tasks"""
    try:
        logger.info("🚀 STARTING BATCH TASK CREATION")
        logger.info("=" * 60)
        
        # Get stored submissions
        stored_submissions = get_stored_submissions()
        if not stored_submissions:
            logger.info("📭 No stored submissions found")
            return
        
        # Load processed submissions
        processed_submissions = load_processed_submissions()
        
        # Process new submissions
        new_count = 0
        failed_count = 0
        
        for submission in stored_submissions:
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
                    failed_count += 1
                    logger.error(f"❌ Failed to process submission: {submission_id}")
        
        # Save processed submissions
        if new_count > 0:
            save_processed_submissions(processed_submissions)
            logger.info(f"🎉 BATCH PROCESSING COMPLETE")
            logger.info(f"   ✅ Successfully created: {new_count} tasks")
            logger.info(f"   ❌ Failed: {failed_count} tasks")
        else:
            logger.info("📭 No new submissions to process")
            
    except Exception as e:
        logger.error(f"❌ Error in batch processing: {str(e)}")

def main():
    """Main function"""
    print("🚀 BATCH TASK CREATOR")
    print("=" * 50)
    print("This will extract stored form data and create all Asana tasks")
    print("=" * 50)
    
    # Process batch submissions
    process_batch_submissions()
    
    print("\n✅ Batch processing complete!")

if __name__ == '__main__':
    main()
