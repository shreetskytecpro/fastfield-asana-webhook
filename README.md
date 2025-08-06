# FastField to Asana Automation

This project automates FastField form submissions and creates corresponding tasks in Asana. It uses Selenium for web automation and the Asana API for task management.

## Features

- ✅ Automated FastField form submission
- ✅ Asana task creation with form data
- ✅ Batch processing capabilities
- ✅ Scheduled automation
- ✅ Comprehensive logging
- ✅ Error handling and retry logic
- ✅ Customizable form field mappings
- ✅ Headless mode support

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Asana Personal Access Token (PAT)
- FastField form URL and credentials (if required)

## Installation

1. **Clone or download this project**
   ```bash
   cd fastfield-asana-automation
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   ```
   
   Edit the `.env` file with your actual values:
   ```
   FASTFIELD_URL=https://your-fastfield-form-url.com
   FASTFIELD_USERNAME=your_username
   FASTFIELD_PASSWORD=your_password
   ASANA_PAT=your_asana_personal_access_token
   ASANA_WORKSPACE_ID=your_workspace_id
   ASANA_PROJECT_ID=your_project_id
   ```

## Configuration

### 1. FastField Form Setup

Edit `config.py` to match your FastField form structure:

```python
FORM_FIELD_MAPPINGS = {
    'name': 'input[name="name"]',
    'email': 'input[name="email"]',
    'phone': 'input[name="phone"]',
    'message': 'textarea[name="message"]',
    'submit_button': 'button[type="submit"]'
}
```

### 2. Asana Setup

1. **Get your Personal Access Token:**
   - Go to Asana → Settings → Apps → Manage Developer Apps
   - Create a new app and copy the Personal Access Token

2. **Find your Workspace ID:**
   - Go to Asana → Settings → Account Settings
   - The workspace ID is in the URL: `https://app.asana.com/0/{workspace_id}/...`

3. **Find your Project ID:**
   - Open your project in Asana
   - The project ID is in the URL: `https://app.asana.com/0/{workspace_id}/{project_id}/...`

### 3. Customize Task Template

Edit the task template in `config.py`:

```python
ASANA_TASK_TEMPLATE = {
    'name': 'FastField Submission: {name}',
    'notes': 'Email: {email}\nPhone: {phone}\nMessage: {message}',
    'tags': ['fastfield', 'automated']
}
```

## Usage

### 1. Test Individual Components

**Test FastField automation:**
```bash
python fastfield_automation.py
```

**Test Asana integration:**
```bash
python asana_integration.py
```

### 2. Run Complete Automation

**Single form submission:**
```python
from main_automation import FastFieldAsanaAutomation

automation = FastFieldAsanaAutomation()
form_data = {
    'name': 'John Doe',
    'email': 'john@example.com',
    'phone': '555-123-4567',
    'message': 'Test submission'
}

success, task = automation.process_form_and_create_task(form_data)
```

**Batch processing:**
```python
batch_data = [
    {'name': 'Alice', 'email': 'alice@example.com', ...},
    {'name': 'Bob', 'email': 'bob@example.com', ...}
]

results = automation.process_batch_forms(batch_data)
```

**Run main automation:**
```bash
python main_automation.py
```

### 3. Scheduled Automation

The main script includes a scheduler that runs every hour. You can modify the schedule in `main_automation.py`:

```python
# Run every 30 minutes
schedule.every(30).minutes.do(automation.run_scheduled_automation)

# Run daily at 9 AM
schedule.every().day.at("09:00").do(automation.run_scheduled_automation)
```

## File Structure

```
fastfield-asana-automation/
├── config.py                 # Configuration settings
├── fastfield_automation.py   # FastField web automation
├── asana_integration.py      # Asana API integration
├── main_automation.py        # Main automation script
├── requirements.txt          # Python dependencies
├── env_example.txt          # Environment variables template
├── README.md                # This file
└── logs/                    # Log files (created automatically)
```

## Troubleshooting

### Common Issues

1. **ChromeDriver not found:**
   - The script automatically downloads ChromeDriver
   - If issues persist, manually download from https://chromedriver.chromium.org/

2. **Asana authentication failed:**
   - Verify your PAT is correct
   - Check that your PAT has the necessary permissions

3. **Form fields not found:**
   - Inspect your FastField form to get correct CSS selectors
   - Update `FORM_FIELD_MAPPINGS` in `config.py`

4. **Rate limiting:**
   - Add delays between submissions
   - Reduce batch sizes

### Debug Mode

Set `HEADLESS_MODE=False` in your `.env` file to see the browser in action:

```
HEADLESS_MODE=False
```

### Logs

Check the log files for detailed information:
- `fastfield_automation.log` - FastField automation logs
- `automation.log` - Main automation logs

## Customization

### Adding Custom Fields

1. **Update form mappings:**
   ```python
   FORM_FIELD_MAPPINGS = {
       'name': 'input[name="name"]',
       'email': 'input[name="email"]',
       'custom_field': 'input[name="custom_field"]',
       'submit_button': 'button[type="submit"]'
   }
   ```

2. **Update task template:**
   ```python
   ASANA_TASK_TEMPLATE = {
       'name': 'FastField Submission: {name}',
       'notes': 'Email: {email}\nCustom Field: {custom_field}',
       'tags': ['fastfield', 'automated']
   }
   ```

### Data Sources

You can modify the automation to read data from:
- CSV files
- Database
- API endpoints
- Excel files

Example CSV integration:
```python
import pandas as pd

df = pd.read_csv('form_data.csv')
for _, row in df.iterrows():
    form_data = row.to_dict()
    automation.process_form_and_create_task(form_data)
```

## Security Notes

- Never commit your `.env` file to version control
- Keep your Asana PAT secure
- Use environment variables for sensitive data
- Consider using a dedicated Asana app for production

## Support

For issues or questions:
1. Check the log files for error details
2. Verify your configuration settings
3. Test individual components first
4. Ensure all dependencies are installed

## License

This project is provided as-is for educational and automation purposes. 