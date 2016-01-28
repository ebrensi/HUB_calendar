#/usr/bin/env python

"""
Created on Wed Mar 25 15:57:01 2015

@author: Efrem

1/27/2016 this is a continuation of the IHO space an utilization analysis
project that was first done in March 2015.

"""

import pandas as pd
import matplotlib.pyplot as plt
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re

"""
  We assume that initial data is in the form of a CSV file output by something
  like gcal2excel, with fields 'Title', 'Start', 'End', 'Where', and 'Calendar'
"""

# 3/10/2014 is the date that Hub staff started using consistent
#  labling of events

# This is the name for the room label classification
Event_Location_Label = 'Loc'

floor_space = ['BROADWAY', 'GALLERY', 'ATRIUM', 'JINGLETOWN', 'ENTIRE']
conf_rooms = ['UPTOWN', 'DOWNTOWN', 'EAST_OAK', 'WEST_OAK', 'MERIDIAN']
other_space = ['MEDITATION', 'KITCHEN']
status = ['HOLD', 'CLOSED']

date_format = '%m-%d-%y  %I:%M %p'


def parse_calendar(infile, outfile, start_date='', end_date='', calendars=[]):
    print("Parsing Calendar file {}...".format(infile))
    df = pd.read_csv(infile)

    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])

    if start_date:
        df = df[df.Start >= start_date]

    if end_date:
        df = df[df.Start <= end_date]

    if calendars:
        df = df[df['Calendar'].isin(calendars)]

    dd = df['End'] - df['Start']
    df['Duration'] = dd / pd.np.timedelta64(1, 'h')

    # drop all duplicates of Title, Start and End field
    df = df.drop_duplicates(subset=['Title', 'Start', 'End'])

    # sort by start datetime and reindex
    df = df.sort('Start').reset_index(drop=True)

    # get rid of extraneous blank lines in Description
    df.Description = df.Description.str.replace('[\r\n]+', '\n')

    #  Here we attempt to extract location info for every calendar event

    # These are the exact uppper case labels associated with most events on
    #  hub calendar in the 'Title' field.  First we try to match them exactly
    labels = {'GALLERY': ['OMI', 'GALLERY'],
              'ATRIUM': ['ATRIUM'],
              'BROADWAY': ['BROADWAY', 'MAIN STAGE', 'MAIN FLOOR', 'MAIN SPACE'],
              'JINGLETOWN': ['JINGLETOWN'],
              'MERIDIAN': ['MERIDIAN', 'meri?di?an(?! university)'],
              'DOWNTOWN': ['DOWNTOWN'],
              'UPTOWN': ['UPTOWN'],
              'WEST_OAK': ['WEST[ |-]?OAK'],
              'EAST_OAK': ['EAST[ |-]?OAK'],
              'KITCHEN': ['KITCHEN', 'Sexy Salad'],
              'MEDITATION': ['MEDITATION'],
              'ENTIRE': ['ENTIRE SPACE', 'WHOLE SPACE'],
              'CLOSED': ['CLOSED',
                         '(?:de)?[ -]?install(?:ation)?', 'Booked due to',
                         'event use',
                         'cancell?ed', 'not available', 'event prep',
                         'storage', 'Co-?Working', 'set ?up'],
              'HOLD': ['HOLD']
              }

    # ********* Find exact label matches in Title and Where text *************
    title_exclude_text = ['meridian university']
    title = df['Title']

    for exclusion in title_exclude_text:
        title = title.str.replace(exclusion, '', case=False)

    where_exclude_text = ["Impact Hub Oakland", "2323", "Broadway",
                          "Oakland, CA", "94612", "United States", ",",
                          'conference room', 'conf room']
    where = df['Where']
    for exclusion in where_exclude_text:
        where = where.str.replace(exclusion, '', case=False)

    text = title.fillna('') + " : " + where.fillna('')

    for sup_label in labels.keys():
        print('***** {} *****'.format(sup_label))
        for label in labels[sup_label]:
            print('Title/Where text containing {}:'.format(label))
            text_contains_label = text.str.contains(
                label, case=False, na=False)

            if sup_label in df.columns:
                df[sup_label] = df[sup_label] | text_contains_label
            else:
                df[sup_label] = text_contains_label

            if any(text_contains_label):
                print(text[text_contains_label])
                print()
                text.loc[text_contains_label] = text.loc[
                    text_contains_label].str.replace(label, '', case=False)
            print('{} records contain {} in Title/Where'
                  .format(text_contains_label.sum(), label))
        print('***** {} records contain {} in Title/Where *****'
              .format(df[sup_label].sum(), sup_label))

    # Check Description field for cancellations
    Description_contains_cancelled = (df.Description
                                      .str
                                      .contains('cancel',


                                                na=False, case=False))

    df['CLOSED'] = df['CLOSED'] | Description_contains_cancelled

    text = text.str.replace('meditation', '', case=False)

    # ********* Do Fuzzy matches in remaining text *************
    print('\n\tInexact matches:')
    match_terms = labels.keys()
    estimates = text.map(lambda x: process.extractOne(x, match_terms))
    good = estimates.map(lambda x: x[1]) > 75
    for idx in df[good].index:
        guessed_label = estimates[idx][0]
        df.loc[idx, guessed_label] = True
        print('"{}" contains {}'.format(text[idx], guessed_label))

    # Change data format from wide to long
    room_labels = floor_space + conf_rooms + other_space
    rooms_stacked = df.ix[:, room_labels].stack()
    room_column = pd.Series(rooms_stacked.index.get_level_values(1),
                            rooms_stacked.index.get_level_values(0),
                            name=Event_Location_Label)[rooms_stacked.values]

    status_labels = status
    status_stacked = df.ix[:, status_labels].stack()
    status_column = pd.Series(status_stacked.index.get_level_values(1),
                              status_stacked.index.get_level_values(0),
                              name='Status')[status_stacked.values]

    df2 = df.drop(status_labels + room_labels, axis=1)
    df2 = df2.join(room_column, how='left').join(status_column, how='left')

    df2[Event_Location_Label] = df2[Event_Location_Label].astype("category")
    df2['Status'] = df2['Status'].astype("category")
    df2['Calendar'] = df2['Calendar'].astype("category")

    if outfile:
        fields = ["Title", "Where", "Loc", "Status", "Start", "End", "Duration",
                  "Created by", "Description", "Calendar"]
        df2[fields].to_csv(outfile, ignore_index=True)
        print('...Wrote "{}"'.format(outfile))

    return df2


def import_parsed_csv(filename):
    df = pd.read_csv(filename)
    df['Start'] = pd.to_datetime(df['Start'])
    df[Event_Location_Label] = df[Event_Location_Label].astype("category")
    if 'Status' in df.columns:
        df['Status'] = df['Status'].astype("category")

    if 'Calendar' in df.columns:
        df['Calendar'] = df['Calendar'].astype("category")
    return df


# ****************************************************************************
def main():
    # df = parse_calendar("IHO_cal_All.csv", "classified_2015.csv",
    #                     start_date="1/1/2015",
    #                     end_date="12/31/2015",
    #                     calendars=["Conference Room"])

    df = parse_calendar("IHO_cal_All.csv",
                        start_date="1/1/2015",
                        end_date="12/31/2015",
                        calendars=["Conference Room"])


if __name__ == "__main__":
    main()
