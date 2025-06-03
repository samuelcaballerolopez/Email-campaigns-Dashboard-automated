import json
import requests
from time import sleep, time
import logging
import datetime
import os
import gspread
import pandas as pd

# --- Configuration ---
API_KEY = os.environ.get("BREVO_API_KEY_CLIENT_1")
URL_BREVO_CAMPAIGNS = "https://api.brevo.com/v3/emailCampaigns"
LOG_FILE = "brevo_to_sheets.log"
LIMIT = 50
WAIT_TIME = 10
SPREADSHEET_KEY = "your Google Sheets spreadsheet key"
WORKSHEET_NAME = "your Google Sheets worksheet name"

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,  # INFO for production, DEBUG for more detail
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Functions ---

def get_brevo_data_with_globalstats(brevo_base_url, headers, limit_per_page):
    """
    Gets Brevo campaign data, including globalStats, sent date, and list IDs,
    and prepares it for Google Sheets.
    """
    offset = 0
    current_page = 1
    all_campaign_data_for_sheets = []
    logging.info("Starting retrieval of Brevo campaign data with globalStats...")

    while True:
        logging.info(f"--- Requesting Page {current_page} of campaigns ---")
        paginated_url = f"{brevo_base_url}?limit={limit_per_page}&offset={offset}&statistics=globalStats"
        logging.info(f"Making request to: {paginated_url}")

        try:
            response = requests.get(paginated_url, headers=headers)
            response.raise_for_status()
            brevo_page_data = response.json()
            logging.debug(f"Full JSON response from Brevo (Page {current_page}, Offset {offset}):\n"
                          f"{json.dumps(brevo_page_data, indent=4, ensure_ascii=False)}")
            
            num_campaigns_received = 0
            if 'campaigns' in brevo_page_data and brevo_page_data['campaigns'] is not None:
                num_campaigns_received = len(brevo_page_data['campaigns'])
            logging.info(f"Brevo response: Code {response.status_code}. "
                         f"Campaigns on this page: {num_campaigns_received}. Current offset: {offset}.")

            campaign_list = brevo_page_data.get('campaigns')
            if not campaign_list:
                if offset == 0 and num_campaigns_received == 0:
                    logging.warning("No campaigns found on the first page.")
                else:
                    logging.info("No more campaigns to retrieve.")
                break

            logging.info(f"Processing {num_campaigns_received} campaigns from page {current_page}:")
            for campaign in campaign_list:
                campaign_id = campaign.get('id')
                campaign_name_value = campaign.get('name', '')
                
                sent_date_str = campaign.get('sentDate')
                formatted_sent_date = ""
                year_val = ""
                month_val = ""
                if sent_date_str:
                    try:
                        if sent_date_str.endswith('Z'):
                            sent_date_str_fixed = sent_date_str.replace("Z", "+00:00")
                        else:
                            sent_date_str_fixed = sent_date_str
                        datetime_obj = datetime.datetime.fromisoformat(sent_date_str_fixed)
                        formatted_sent_date = datetime_obj.strftime('%d-%m-%Y')
                        year_val = str(datetime_obj.year)
                        month_val = str(datetime_obj.month).zfill(2)
                    except ValueError as ve:
                        logging.warning(f"  ID: {campaign_id} - Error parsing sentDate '{sent_date_str}': {ve}. Date will be left empty.")
                    except Exception as e_date:
                        logging.error(f"  ID: {campaign_id} - Unexpected error processing sentDate '{sent_date_str}': {e_date}")

                recipients_data = campaign.get('recipients', {})
                list_ids_array = [] 
                if recipients_data and isinstance(recipients_data, dict):
                    list_ids_array = recipients_data.get('lists', []) 

                formatted_list_ids = "" 
                if list_ids_array: 
                    formatted_list_ids = ", ".join(map(str, list_ids_array))
                
                stats_block = campaign.get('statistics', {})
                global_stats = {}
                if stats_block and isinstance(stats_block, dict):
                    global_stats = stats_block.get('globalStats', {})

                row_data = {
                    "CampaignID": str(campaign_id) if campaign_id else '',
                    "CampaignName": campaign_name_value,
                    "SentDate": formatted_sent_date,
                    "ListID": formatted_list_ids,
                    "UniqueClicks": global_stats.get('uniqueClicks', 0),
                    "Clickers": global_stats.get('clickers', 0), 
                    "Complaints": global_stats.get('complaints', 0),
                    "Delivered": global_stats.get('delivered', 0),
                    "Sent": global_stats.get('sent', 0),
                    "SoftBounces": global_stats.get('softBounces', 0),
                    "HardBounces": global_stats.get('hardBounces', 0),
                    "UniqueViews": global_stats.get('uniqueViews', 0),
                    "TrackableViews": global_stats.get('trackableViews', 0),
                    "Unsubscriptions": global_stats.get('unsubscriptions', 0),
                    "Viewed": global_stats.get('viewed', 0),
                    "Deferred": global_stats.get('deferred', 0),
                    "Year": year_val,
                    "Month": month_val
                }
                all_campaign_data_for_sheets.append(row_data)
                logging.debug(f"  Data processed for ID {campaign_id}: {row_data.get('CampaignName')}, ListIDs: '{formatted_list_ids}', globalStats present: {bool(global_stats)}")
            
            if num_campaigns_received == limit_per_page:
                logging.info(f"Waiting {WAIT_TIME} seconds before the next page...")
                sleep(WAIT_TIME)
            offset += limit_per_page
            current_page += 1
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"HTTP error when contacting Brevo: {http_err}")
            if http_err.response is not None: 
                logging.error(f"Status code: {http_err.response.status_code}")
                if hasattr(http_err.response, 'text'):
                    logging.error(f"Server response (HTTP error): {http_err.response.text}")
            break 
        except requests.exceptions.RequestException as req_err:
            logging.error(f"Network or request error (non-HTTP) when contacting Brevo: {req_err}")
            break 
        except json.JSONDecodeError as json_err:
            logging.error(f"Error decoding Brevo JSON response: {json_err}")
            if 'response' in locals() and response and hasattr(response, 'text'):
                logging.error(f"Response text (not JSON): {response.text}")
            break
        except Exception as e:
            logging.error(f"Unexpected error during data retrieval: {e}", exc_info=True)
            break
    logging.info(f"Brevo data retrieval finished. {len(all_campaign_data_for_sheets)} rows processed for Google Sheets.")
    return all_campaign_data_for_sheets

# --- MODIFICATION HERE: The function now expects the JSON STRING of the credentials ---
def send_to_google_sheets(data_list, credentials_json_string, spreadsheet_key, worksheet_name):
    """Sends data to Google Sheets, replacing existing content, using a JSON string for credentials."""
    
    if not credentials_json_string:
        logging.error("Google credentials JSON string was not provided.")
        return
    
    logging.info(f"Attempting to send {len(data_list)} rows to Google Sheets: '{worksheet_name}'...")
    try:
        # --- MODIFICATION HERE: Authenticate using the JSON string ---
        credentials_dict = json.loads(credentials_json_string)
        gc = gspread.service_account_from_dict(credentials_dict)
        # --- END OF MODIFICATION ---
        
        logging.info(f"Opening spreadsheet with key: {spreadsheet_key}")
        sh = gc.open_by_key(spreadsheet_key)
        
        logging.info(f"Accessing worksheet: {worksheet_name}")
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            logging.warning(f"Worksheet '{worksheet_name}' not found. Attempting to create.")
            worksheet = sh.add_worksheet(title=worksheet_name, rows="1", cols="20") 
        logging.info("Clearing previous sheet content...")
        worksheet.clear()
        logging.info("Previous content cleared.")

        if not data_list:
            logging.warning("No data to send to Google Sheets.")
            return
        
        df = pd.DataFrame(data_list)
        column_order = [ 
            "CampaignID", "CampaignName", "SentDate", "ListID",
            "UniqueClicks", "Clickers", "Complaints", "Delivered", "Sent", 
            "SoftBounces", "HardBounces", "UniqueViews", "TrackableViews",
            "Unsubscriptions", "Viewed", "Deferred", "Year", "Month"
        ]
        df_ordered = pd.DataFrame()
        present_columns_in_order = []
        for col_name in column_order:
            if col_name in df.columns:
                df_ordered[col_name] = df[col_name]
                present_columns_in_order.append(col_name)
            else:
                logging.warning(f"Column '{col_name}' defined in column_order was not found in Brevo data. It will be omitted.")
        
        for col_name in df.columns:
            if col_name not in present_columns_in_order:
                df_ordered[col_name] = df[col_name]
                present_columns_in_order.append(col_name)
        
        df_to_send = df_ordered
        logging.info(f"Preparing to write {len(df_to_send)} rows with {len(present_columns_in_order)} columns.")
        df_to_send = df_to_send.astype(str)
        worksheet.update([present_columns_in_order] + df_to_send.values.tolist(), value_input_option='USER_ENTERED')
        logging.info(f"Data successfully sent to Google Sheets. Rows written: {len(df_to_send)}")

    except json.JSONDecodeError as json_err_gcred:
        logging.error(f"Error decoding Google JSON credentials: {json_err_gcred}. "
                      "Ensure the GOOGLE_CREDENTIALS_JSON environment variable contains valid JSON.")
    except gspread.exceptions.GSpreadException as gspread_err:
        logging.error(f"gspread error interacting with Google Sheets: {gspread_err}")
    except Exception as e:
        logging.error(f"Unexpected error sending data to Google Sheets: {e}", exc_info=True)

def main():
    """Main script function."""
    logging.info("Starting script to extract Brevo data and send to Google Sheets (GitHub version)...")

    # Check if API_KEY (loaded from environment variable) is available
    if not API_KEY:
        logging.error("Brevo API Key from environment variable 'BREVO_API_KEY_CLIENT_1' not found or is empty.")
        return

    # Use environment variable for Google credentials ---
    google_credentials_json_string = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not google_credentials_json_string:
        logging.error("Environment variable 'GOOGLE_CREDENTIALS_JSON' not found or empty. "
                      "Will not be able to authenticate with Google Sheets.")
        # Consider if the script should fail or continue without sending to Sheets
        # return # Uncomment if you want the script to fail here

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
    }

    all_campaign_data = get_brevo_data_with_globalstats(
        URL_BREVO_CAMPAIGNS, 
        headers, 
        limit_per_page=LIMIT
    )

    if all_campaign_data:
        if google_credentials_json_string: # Only attempt to send if credentials were loaded
            send_to_google_sheets(
                all_campaign_data, 
                google_credentials_json_string, # Pass the JSON STRING
                SPREADSHEET_KEY, 
                WORKSHEET_NAME
            )
        else:
            logging.warning("Data will not be sent to Google Sheets because JSON credentials are not available in the environment variable.")
            logging.info("Data retrieved from Brevo (not sent to Sheets):")
            # Log some data to verify that the retrieval worked
            for i, row in enumerate(all_campaign_data[:3]): # Shows the first 3 rows
                logging.info(f"Sample row {i+1}: {json.dumps(row, ensure_ascii=False)}")
    else:
        logging.info("No data retrieved from Brevo or the data list is empty.")

    logging.info("Script finished.")

if __name__ == "__main__":
    main()
    # For scheduled executions with GitHub Actions, you will configure the cron in the .yml workflow file.
