import streamlit as st
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta

# URL of the data
url = "http://172.16.0.207/OTRS_system/Download11.php?process=xidops"

st.title("Data Viewer")

# Allow the user to select a range of dates for filtering
start_date = st.date_input("Select the start date", min_value=datetime(2000, 1, 1), max_value=datetime.today(), value=datetime.today())
end_date = st.date_input("Select the end date", min_value=start_date, max_value=datetime.today(), value=datetime.today())

# Generate the range of dates
selected_dates = pd.date_range(start=start_date, end=end_date).date

if st.button("Fetch Data"):
    try:
        # Fetch the data from the URL
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors

        # Convert the response text to a StringIO object to simulate file-like behavior
        csv_data = StringIO(response.text)

        # Read the CSV data into a DataFrame with proper parsing
        df = pd.read_csv(csv_data, delimiter=',', quotechar='\"', skip_blank_lines=True, on_bad_lines='skip')

        # Check if the DataFrame has more columns than expected
        if df.shape[1] == 24:
            # Remove the 24th column if it exists
            df = df.iloc[:, :23]

        # Create a new DataFrame with "username", "resolved", and "first_closed_ticket_timestamp" columns
        if "username" in df.columns and "resolved" in df.columns and "first_closed_ticket_timestamp" in df.columns:
            # Select the necessary columns
            df_cleaned = df[["username", "resolved", "first_closed_ticket_timestamp"]]
        else:
            st.error("The required columns 'username', 'resolved' or 'first_closed_ticket_timestamp' are not found in the data.")
            st.write("Columns in the dataset:", df.columns.tolist())
            # Exit the script execution for this button click
            st.stop()

        # Set pandas options to improve readability
        pd.options.display.max_columns = None  # Display all columns
        pd.options.display.max_colwidth = 50  # Adjust column width for readability
        pd.options.display.float_format = '{:,.2f}'.format  # Format floats to two decimal places

        # Convert 'resolved' column to numeric and 'first_closed_ticket_timestamp' to datetime
        df_cleaned['resolved'] = pd.to_numeric(df_cleaned['resolved'], errors='coerce')
        df_cleaned['first_closed_ticket_timestamp'] = pd.to_datetime(df_cleaned['first_closed_ticket_timestamp'], errors='coerce')

        # Filter for open tickets (0 or 2 in resolved column) for all dates (no date filter applied here)
        open_tickets = df_cleaned[df_cleaned['resolved'].isin([0, 2])]
        open_tickets_summary = open_tickets.groupby('username').size().reset_index(name='Open tickets')

        # Filter for resolved tickets (1 in resolved column) for the selected dates
        resolved_selected_dates = df_cleaned[(df_cleaned['resolved'] == 1) & (df_cleaned['first_closed_ticket_timestamp'].dt.date.isin(selected_dates))]

        # Group by username and count resolved tickets for the selected dates
        resolved_selected_dates_summary = resolved_selected_dates.groupby('username').size().reset_index(name='Resolved on Selected Dates')

        # Display the Open Tickets Summary table (no date filter applied)
        st.write("Open Tickets Summary:")
        st.dataframe(open_tickets_summary)

        # Display the Resolved on Selected Dates Summary table
        st.write(f"Resolved Tickets on Selected Dates: {', '.join(map(str, selected_dates))}")
        st.dataframe(resolved_selected_dates_summary)

        # Save the cleaned DataFrame to an Excel file
        excel_file_path = "cleaned_data_username_resolved.xlsx"
        df_cleaned.to_excel(excel_file_path, index=False)  # Save with column headers
        st.success(f"Data saved to {excel_file_path}")

        # Allow users to download the cleaned data as a CSV
        csv_output = df_cleaned.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Cleaned Data (Username and Resolved) as CSV",
            data=csv_output,
            file_name="cleaned_data_username_resolved.csv",
            mime="text/csv"
        )
    except requests.exceptions.RequestException as req_error:
        st.error(f"Failed to fetch data: {req_error}")
    except pd.errors.ParserError as parse_error:
        st.error(f"Error parsing CSV data: {parse_error}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
    