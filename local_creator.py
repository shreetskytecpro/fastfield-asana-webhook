#!/usr/bin/env python3
"""
Local Asana Task Creator
Create tasks directly from your machine
"""

import requests
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asana configuration
ASANA_PAT = "2/1210137074577902/1210777453181763:2b48ddc6283d9c71f6f40576780739d9"
PROJECT_ID = "1210717842641983"

def create_asana_task(form_data):
    """Create Asana task with provided data"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        logger.info("📋 CREATING ASANA TASK")
        logger.info(f"   Name: {form_data['task_name']}")
        logger.info(f"   Due Date: {form_data['due_date']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        
        # Create basic task
        task_data = {
            'data': {
                'name': form_data['task_name'],
                'notes': '',
                'projects': [PROJECT_ID],
                'due_date': form_data['due_date']
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
            update_custom_fields(task_id, form_data)
            
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

def update_custom_fields(task_id, form_data):
    """Update custom fields"""
    try:
        headers = {
            'Authorization': f'Bearer {ASANA_PAT}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"🔧 UPDATING CUSTOM FIELDS FOR TASK {task_id}")
        
        # Get available custom fields
        response = requests.get(
            f'https://app.asana.com/api/1.0/tasks/{task_id}',
            headers=headers,
            params={'opt_fields': 'custom_fields'}
        )
        
        if response.status_code == 200:
            task_data = response.json()['data']
            custom_fields = task_data.get('custom_fields', [])
            
            logger.info(f"   Found {len(custom_fields)} custom fields")
            
            # Prepare updates
            field_updates = {}
            
            # Update Job Number field
            for field in custom_fields:
                if field.get('name') == 'Jb No' and form_data['job_number']:
                    field_updates[field.get('gid')] = form_data['job_number']
                    logger.info(f"   ✅ Job Number: {form_data['job_number']}")
                    break
            
            # Update Received Date field
            for field in custom_fields:
                if field.get('name') == 'Received Date' and form_data['accepted_date']:
                    field_updates[field.get('gid')] = form_data['accepted_date']
                    logger.info(f"   ✅ Received Date: {form_data['accepted_date']}")
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
            else:
                logger.info("   ⚠️ No custom fields to update")
        
    except Exception as e:
        logger.error(f"❌ Error updating custom fields: {str(e)}")

def create_task_manually():
    """Create a task by manually entering data"""
    print("\n📋 MANUAL TASK CREATION")
    print("=" * 50)
    
    # Get data from user
    task_name = input("Enter Task Name (Address): ").strip()
    job_number = input("Enter Job Number: ").strip()
    accepted_date = input("Enter Accepted Date (MM/DD/YYYY): ").strip()
    due_date = input("Enter Due Date (MM/DD/YYYY): ").strip()
    
    form_data = {
        'task_name': task_name,
        'job_number': job_number,
        'accepted_date': accepted_date,
        'due_date': due_date
    }
    
    result = create_asana_task(form_data)
    return result

def process_webhook_file():
    """Process webhook data from a JSON file"""
    print("\n📁 PROCESS WEBHOOK FROM FILE")
    print("=" * 50)
    
    file_path = input("Enter the path to your webhook JSON file: ").strip()
    
    try:
        with open(file_path, 'r') as f:
            webhook_data = json.load(f)
        
        logger.info(f"📄 Loaded webhook data from {file_path}")
        
        # Extract data from webhook
        form_data = {}
        form_data['task_name'] = webhook_data.get('alpha_2', 'Unknown Address')
        
        # Job Number
        job_number = ''
        if webhook_data.get('lookuplistpicker_1'):
            if isinstance(webhook_data['lookuplistpicker_1'], dict):
                selected_values = webhook_data['lookuplistpicker_1'].get('selectedValues', [])
                job_number = selected_values[0] if selected_values else ''
            elif isinstance(webhook_data['lookuplistpicker_1'], list):
                job_number = webhook_data['lookuplistpicker_1'][0] if webhook_data['lookuplistpicker_1'] else ''
            else:
                job_number = webhook_data['lookuplistpicker_1']
        form_data['job_number'] = job_number
        
        # Dates
        accepted_date = None
        if webhook_data.get('datepicker_1'):
            try:
                accepted_date = datetime.fromisoformat(webhook_data['datepicker_1'].replace('Z', '+00:00'))
            except:
                try:
                    accepted_date = datetime.fromisoformat(webhook_data['datepicker_1'])
                except:
                    accepted_date = datetime.now()
        else:
            accepted_date = datetime.now()
        
        form_data['accepted_date'] = accepted_date.strftime('%m/%d/%Y')
        form_data['due_date'] = (accepted_date + timedelta(days=5)).strftime('%m/%d/%Y')
        
        logger.info(f"   Task Name: {form_data['task_name']}")
        logger.info(f"   Job Number: {form_data['job_number']}")
        logger.info(f"   Accepted Date: {form_data['accepted_date']}")
        logger.info(f"   Due Date: {form_data['due_date']}")
        
        result = create_asana_task(form_data)
        return result
        
    except FileNotFoundError:
        logger.error(f"❌ File not found: {file_path}")
        return {'success': False, 'message': 'File not found'}
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON in file: {file_path}")
        return {'success': False, 'message': 'Invalid JSON'}
    except Exception as e:
        logger.error(f"❌ Error reading file: {str(e)}")
        return {'success': False, 'message': f'Error reading file: {str(e)}'}

def main():
    """Main menu"""
    print("🚀 LOCAL ASANA TASK CREATOR")
    print("=" * 50)
    print("1. Create task manually")
    print("2. Process webhook from JSON file")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            result = create_task_manually()
            print(f"\n✅ Result: {result['message']}")
            
        elif choice == '2':
            result = process_webhook_file()
            print(f"\n✅ Result: {result['message']}")
            
        elif choice == '3':
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")

if __name__ == '__main__':
    main()
