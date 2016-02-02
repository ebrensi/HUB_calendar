## 2015 IHO Space Utilization Analysis via calendar records
This repository contains the scripts for parsing room booking info from Oakland Impact Hub's events calendar and determining how close we are to optimal space utilization.

### Workflow
  1. Parse the text from IHO Google Calendars into a CSV file with [gcal2excel](https://www.gcal2excel.com)
  2. Determine hours booked and count of number of rentals over the year 2015 for each rentable space in categories:
    1. `conf_rooms = ['UPTOWN', 'DOWNTOWN', 'EAST_OAK', 'WEST_OAK', 'MERIDIAN']`
    2. `floor_space = ['BROADWAY', 'GALLERY', 'ATRIUM', 'JINGLETOWN', 'ENTIRE']`
  3. Classify each space usage event as
    * `DAY`: Events beginning 8:00 - 17:30
    * `EVENING`: "         " 17:30 - 24:00
  4. Determine rental capacity of IHO:
    *  9.5 day hours and 6.5 evening hours comprises one rental day
    * 251 work days and 105 weekend days in 2015, according to http://www.workingdays.us/workingdays_holidays_2015.htm
  5. Compute percentage of capacity for each room
  6. Present the findings in an Excel doc


### Data
The original data are in two Google calendars used by IHO.  We grabbed those fields and put them in a CSV file.  Time information is already standardized but event description and location are human written into a general "Description" text field.  [`IHO_cal.py`](IHO_cal.py) parses the text from that CSV and catgorizes calendar entries.  The relevant data are contained in [`IHO_space_util_2015.csv`](IHO_space_util_2015.csv). Note that if multiple rooms are specified in a calendar entry, each room has a separate row in `IHO_space_util_2015.csv`.


### Questions
Aside from percentage capacity we might want to know:
  * How do results compare with 2014?
  * What is the minimum space utilization that sustains IHO financially?

