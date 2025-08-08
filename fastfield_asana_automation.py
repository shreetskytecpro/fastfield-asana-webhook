#!/usr/bin/env python3
"""
🚀 FASTFIELD TO ASANA AUTOMATION - ALL-IN-ONE
Complete automation system for FastField forms to Asana tasks

Features:
- Extract data from Heroku webhook storage
- Extract data from local JSON files
- Create Asana tasks with proper field mapping
- Handle custom fields (Job Number, Received Date)
- Create subtasks for Location Failures
- Batch processing with duplicate prevention
- Manual task creation
"""

import requests
import json
import logging
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Asana Configuration
ASANA_PAT = "2/1210137074577902/1210777453181763:2b48ddc6283d9c71f6f40576780739d9"
PROJECT_ID = "1210717842641983"

# Heroku Configuration
HEROKU_BASE_URL = "https://fastfield-asana-webhook-e5e82c557bf4.herokuapp.com"

# Local files
PROCESSED_FILE = 'processed_submissions.json'

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

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

# =============================================================================
# DATA EXTRACTION FUNCTIONS
# =============================================================================

def get_heroku_data():
    """Get real unprocessed data from Heroku"""
    try:
        url = f"{HEROKU_BASE_URL}/unprocessed_data"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            unprocessed_submissions = data.get('unprocessed_submissions', [])
            logger.info(f"📊 Found {len(unprocessed_submissions)} unprocessed submissions on Heroku")
            
            # Extract raw_data from each submission
            real_submissions = []
            for submission in unprocessed_submissions:
                raw_data = submission.get('raw_data', {})
                if raw_data:
                    real_submissions.append(raw_data)
            
            logger.info(f"📄 Extracted {len(real_submissions)} real form submissions")
            return real_submissions
        else:
            logger.error(f"❌ Failed to get Heroku data: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error getting Heroku data: {str(e)}")
        return []

def get_local_json_data(file_path):
    """Get data from local JSON file"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # If it's a single submission, wrap in list
        if isinstance(data, dict):
            data = [data]
        
        logger.info(f"📄 Loaded {len(data)} submissions from {file_path}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Error loading local file {file_path}: {str(e)}")
        return []

def mark_processed_on_heroku(submission_ids):
    """Mark submissions as processed on Heroku"""
    try:
        url = f"{HEROKU_BASE_URL}/mark_processed"
        
        response = requests.post(
            url,
            json={'submission_ids': submission_ids},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Marked {data.get('updated_count', 0)} submissions as processed on Heroku")
            return True
        else:
            logger.error(f"❌ Failed to mark processed on Heroku: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error marking processed on Heroku: {str(e)}")
        return False

# =============================================================================
# ASANA TASK CREATION FUNCTIONS
# =============================================================================

def extract_field_data(form_data):
    """Extract and transform FastField data"""
    extracted = {}
    
    # Task name (alpha_2 - Address)
    extracted['task_name'] = form_data.get('alpha_2', 'Unknown Address')
    
    # Job number (lookuplistpicker_1)
    job_number = ''
    if form_data.get('lookuplistpicker_1'):
        if isinstance(form_data['lookuplistpicker_1'], dict):
            selected_values = form_data['lookuplistpicker_1'].get('selectedValues', [])
            job_number = selected_values[0] if selected_values else ''
        elif isinstance(form_data['lookuplistpicker_1'], list):
            job_number = form_data['lookuplistpicker_1'][0] if form_data['lookuplistpicker_1'] else ''
        else:
            job_number = str(form_data['lookuplistpicker_1'])
    extracted['job_number'] = job_number
    
    # Accepted date (datepicker_1)
    accepted_date = datetime.now()
    if form_data.get('datepicker_1'):
        try:
            accepted_date = datetime.fromisoformat(form_data['datepicker_1'].replace('Z', '+00:00'))
        except:
            try:
                accepted_date = datetime.fromisoformat(form_data['datepicker_1'])
            except:
                pass
    extracted['accepted_date'] = accepted_date
    extracted['due_date'] = accepted_date + timedelta(days=5)
    
    # Task assignee (textlabel_2 - Job Owner)
    extracted['task_assignee'] = form_data.get('textlabel_2', '')
    
    # Subtask name (listpicker_4 - Location Failure)
    subtask_name = ''
    if form_data.get('listpicker_4'):
        if isinstance(form_data['listpicker_4'], dict):
            selected_names = form_data['listpicker_4'].get('selectedNames', [])
            subtask_name = selected_names[0] if selected_names else ''
        elif isinstance(form_data['listpicker_4'], list):
            subtask_name = form_data['listpicker_4'][0] if form_data['listpicker_4'] else ''
        else:
            subtask_name = str(form_data['listpicker_4'])
    extracted['subtask_name'] = subtask_name
    
    # Subtask assignee (lookuplistpicker_2)
    subtask_assignee = ''
    if form_data.get('lookuplistpicker_2'):
        if isinstance(form_data['lookuplistpicker_2'], dict):
            selected_names = form_data['lookuplistpicker_2'].get('selectedNames', [])
            subtask_assignee = selected_names[0] if selected_names else ''
        elif isinstance(form_data['lookuplistpicker_2'], list):
            subtask_assignee = form_data['lookuplistpicker_2'][0] if form_data['lookuplistpicker_2'] else ''
        else:
            subtask_assignee = str(form_data['lookuplistpicker_2'])
    extracted['subtask_assignee'] = subtask_assignee
    
    # Overall comments (multiline_3 or multiline_34)
    description = form_data.get('multiline_3', '') or form_data.get('multiline_34', '')
    extracted['description'] = description
    
    return extracted

def create_asana_task(extracted_data):
    """Create Asana task with extracted data"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📋 Creating task: {extracted_data['task_name']}")
        logger.info(f"   Job Number: {extracted_data['job_number']}")
        logger.info(f"   Due Date: {extracted_data['due_date'].strftime('%m/%d/%Y')}")
        logger.info(f"   Description: {extracted_data['description']}")
        
        # Create basic task
        task_data = {
            'data': {
                'name': extracted_data['task_name'],
                'notes': extracted_data['description'],
                'projects': [PROJECT_ID],
                'due_date': extracted_data['due_date'].strftime('%m/%d/%Y')
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
            update_custom_fields(task_id, extracted_data)
            
            # Create subtask if needed
            if extracted_data.get('subtask_name') and extracted_data.get('subtask_assignee'):
                create_subtask(task_id, extracted_data)
            
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

def update_custom_fields(task_id, extracted_data):
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
                if field.get('name') == 'Jb No' and extracted_data['job_number']:
                    field_updates[field.get('gid')] = extracted_data['job_number']
                    logger.info(f"   ✅ Job Number: {extracted_data['job_number']}")
                    break
            
            # Update Received Date field
            for field in custom_fields:
                if field.get('name') == 'Received Date' and extracted_data['accepted_date']:
                    accepted_date_str = extracted_data['accepted_date'].strftime('%m/%d/%Y')
                    field_updates[field.get('gid')] = accepted_date_str
                    logger.info(f"   ✅ Received Date: {accepted_date_str}")
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

def create_subtask(task_id, extracted_data):
    """Create subtask for Location Failures"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📋 Creating subtask: {extracted_data['subtask_name']}")
        logger.info(f"   Assignee: {extracted_data['subtask_assignee']}")
        
        subtask_data = {
            'data': {
                'name': extracted_data['subtask_name'],
                'notes': f"Assignee: {extracted_data['subtask_assignee']}",
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
            logger.info(f"   ✅ Subtask created: {subtask_id}")
        else:
            logger.error(f"   ❌ Failed to create subtask: {response.status_code}")
        
    except Exception as e:
        logger.error(f"❌ Error creating subtask: {str(e)}")

# =============================================================================
# AUTOMATION FUNCTIONS
# =============================================================================

def process_batch_from_heroku():
    """Process all unprocessed submissions from Heroku"""
    try:
        logger.info("🚀 PROCESSING BATCH FROM HEROKU")
        logger.info("=" * 60)
        
        # Get data from Heroku
        submissions = get_heroku_data()
        if not submissions:
            logger.info("📭 No unprocessed submissions found on Heroku")
            return
        
        # Load processed submissions
        processed_submissions = load_processed_submissions()
        
        # Process new submissions
        new_count = 0
        failed_count = 0
        newly_processed_ids = []
        
        for submission in submissions:
            submission_id = submission.get('submissionId', '')
            
            if submission_id and submission_id not in processed_submissions:
                logger.info(f"📊 Processing submission: {submission_id}")
                
                # Extract data
                extracted_data = extract_field_data(submission)
                
                # Create Asana task
                result = create_asana_task(extracted_data)
                
                if result['success']:
                    # Mark as processed
                    processed_submissions.append(submission_id)
                    newly_processed_ids.append(submission_id)
                    new_count += 1
                    logger.info(f"✅ Successfully processed submission: {submission_id}")
                else:
                    failed_count += 1
                    logger.error(f"❌ Failed to process submission: {submission_id}")
        
        # Save processed submissions locally and mark on Heroku
        if new_count > 0:
            save_processed_submissions(processed_submissions)
            
            # Mark submissions as processed on Heroku
            if newly_processed_ids:
                mark_processed_on_heroku(newly_processed_ids)
            
            logger.info(f"🎉 BATCH PROCESSING COMPLETE")
            logger.info(f"   ✅ Successfully created: {new_count} tasks")
            logger.info(f"   ❌ Failed: {failed_count} tasks")
        else:
            logger.info("📭 No new submissions to process")
            
    except Exception as e:
        logger.error(f"❌ Error in batch processing: {str(e)}")

def process_local_json_file(file_path):
    """Process submissions from local JSON file"""
    try:
        logger.info(f"🚀 PROCESSING LOCAL FILE: {file_path}")
        logger.info("=" * 60)
        
        # Get data from local file
        submissions = get_local_json_data(file_path)
        if not submissions:
            logger.info(f"📭 No submissions found in {file_path}")
            return
        
        # Load processed submissions
        processed_submissions = load_processed_submissions()
        
        # Process submissions
        new_count = 0
        failed_count = 0
        
        for submission in submissions:
            submission_id = submission.get('submissionId', f"local-{datetime.now().timestamp()}")
            
            if submission_id not in processed_submissions:
                logger.info(f"📊 Processing submission: {submission_id}")
                
                # Extract data
                extracted_data = extract_field_data(submission)
                
                # Create Asana task
                result = create_asana_task(extracted_data)
                
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
            logger.info(f"🎉 LOCAL FILE PROCESSING COMPLETE")
            logger.info(f"   ✅ Successfully created: {new_count} tasks")
            logger.info(f"   ❌ Failed: {failed_count} tasks")
        else:
            logger.info("📭 No new submissions to process")
            
    except Exception as e:
        logger.error(f"❌ Error processing local file: {str(e)}")

def create_manual_task():
    """Create a task manually with user input"""
    try:
        logger.info("🚀 MANUAL TASK CREATION")
        logger.info("=" * 40)
        
        print("\n📝 Enter task details:")
        
        # Get user input
        task_name = input("Task Name (Address): ").strip()
        job_number = input("Job Number: ").strip()
        description = input("Description: ").strip()
        
        # Use current date + 5 days for due date
        accepted_date = datetime.now()
        due_date = accepted_date + timedelta(days=5)
        
        # Create extracted data structure
        extracted_data = {
            'task_name': task_name or 'Manual Task',
            'job_number': job_number,
            'accepted_date': accepted_date,
            'due_date': due_date,
            'description': description,
            'task_assignee': '',
            'subtask_name': '',
            'subtask_assignee': ''
        }
        
        # Create task
        result = create_asana_task(extracted_data)
        
        if result['success']:
            logger.info(f"✅ Manual task created successfully: {result['task_id']}")
        else:
            logger.error(f"❌ Failed to create manual task: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in manual task creation: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

# =============================================================================
# MAIN MENU
# =============================================================================

def main():
    """Main menu for the automation system"""
    print("🚀 FASTFIELD TO ASANA AUTOMATION")
    print("=" * 50)
    print("1. Process batch from Heroku (Real webhook data)")
    print("2. Process local JSON file")
    print("3. Create manual task")
    print("4. Check Heroku status")
    print("5. Exit")
    print("=" * 50)
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                process_batch_from_heroku()
                
            elif choice == '2':
                file_path = input("Enter JSON file path: ").strip()
                if file_path and os.path.exists(file_path):
                    process_local_json_file(file_path)
                else:
                    print("❌ File not found or invalid path")
                    
            elif choice == '3':
                create_manual_task()
                
            elif choice == '4':
                try:
                    response = requests.get(f"{HEROKU_BASE_URL}/", timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        print(f"\n📊 Heroku Status: {data.get('status', 'Unknown')}")
                        stats = data.get('stats', {})
                        print(f"   Total submissions: {stats.get('total_submissions', 0)}")
                        print(f"   Unprocessed: {stats.get('unprocessed_submissions', 0)}")
                    else:
                        print(f"❌ Failed to get Heroku status: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error checking Heroku: {str(e)}")
                    
            elif choice == '5':
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    main()
