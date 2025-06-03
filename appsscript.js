function generateSimilarRandomData() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getActiveSheet(); // Assumes the active sheet
  // Or specify sheet name if not the active one:
  // const sheet = spreadsheet.getSheetByName("YourSheetName");

  const dataRange = sheet.getDataRange();
  const values = dataRange.getValues(); // Gets all values from the sheet

  const headerRow = values[0]; // The first row is the header
  const numRows = values.length; // Total number of rows
  const numCols = values[0].length; // Total number of columns

  // Column indices to modify (based on the image D=3, P=15)
  // Reminder: JavaScript arrays are 0-indexed.
  // Column D is at index 3. Column P is at index 15.
  const startColIndex = 3; // Column D (index 3)
  const endColIndex = 15;  // Column P (index 15)

  // Variation factor for random data. Adjust this value.
  // A value of 0.1 means +/- 10% variation from the original value.
  const variationFactor = 0.1;

  // Iterate from the second row (index 1) to avoid modifying headers
  for (let row = 1; row < numRows; row++) {
    for (let col = startColIndex; col <= endColIndex; col++) {
      const originalValue = values[row][col];
      let newValue;

      // Ensure the original value is a number and not NaN
      if (typeof originalValue === 'number' && !isNaN(originalValue)) {
        // Logic to generate similar and coherent values
        switch (headerRow[col]) {
          case 'Complaints':
          case 'SoftBounces':
          case 'HardBounces':
          case 'Unique Views': 
          case 'Trackable Views':
          case 'Unsubscriptions':
          case 'Viewed': // This can also have low values
          case 'Deferred':
            // For values that are typically low (0, 1, 2, few digits)
            if (originalValue === 0) {
              newValue = (Math.random() < 0.95) ? 0 : Math.floor(Math.random() * 3) + 1; // 95% chance of 0, else 1-3
            } else if (originalValue === 1) {
              newValue = (Math.random() < 0.7) ? 1 : (Math.random() < 0.9) ? 0 : Math.floor(Math.random() * 3) + 1; // More likely 1, or 0, or 2-4
            } else {
              // Existing small values, add a little noise
              newValue = Math.max(0, Math.round(originalValue * (1 + (Math.random() - 0.5) * variationFactor * 2)));
            }
            break;

         
          case 'UniqueClicks': // This covers Column D based on your image
          case 'Clicks':
            // Values that are often proportional to Sent/Delivered but can vary
            // Tries to maintain a proportion or generate in a wider range if it's 0
            if (originalValue === 0) {
              newValue = (Math.random() < 0.8) ? 0 : Math.floor(Math.random() * 50) + 1; // 80% chance of 0, else 1-50
            } else {
              newValue = Math.max(0, Math.round(originalValue * (1 + (Math.random() - 0.5) * variationFactor * 4))); // Higher variation
            }
            break;

          case 'Delivered':
          case 'Sent':
            // Larger values, percentage variation
            newValue = Math.max(0, Math.round(originalValue * (1 + (Math.random() - 0.5) * variationFactor * 2)));
            // Ensure Delivered is not greater than Sent
            // Note: The previous logic for 'Delivered' checking 'Sent' (col-1) implies 'Sent' is immediately to its left.
            // If your column order changes, this specific check might need adjustment.
            if (headerRow[col] === 'Delivered' && col > 0 && headerRow[col - 1] === 'Sent') {
              const sentValue = values[row][col - 1];
              if (newValue > sentValue) {
                newValue = Math.round(sentValue * (0.9 + Math.random() * 0.1));
              }
            }
            break;

          default:
            // For other numeric columns not specifically handled, apply standard variation
            newValue = Math.max(0, Math.round(originalValue * (1 + (Math.random() - 0.5) * variationFactor * 2)));
            break;
        }
      } else {
        // If not a number, keep the original value
        newValue = originalValue;
      }
      values[row][col] = newValue;
    }
  }

  // Write the new values back to the sheet
  sheet.getRange(1, 1, numRows, numCols).setValues(values);

  Logger.log("Random data generation completed.");
}
