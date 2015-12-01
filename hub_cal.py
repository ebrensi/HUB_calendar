#/usr/bin/env python

# -*- coding: utf-8 -*-
"""
Created on Wed Mar 25 15:57:01 2015

@author: Efrem
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
other_space = ['MEDITATION', 'CORNER', 'KITCHEN']
status = ['HOLD', 'CLOSED']

date_format = '%m-%d-%y  %I:%M %p'


def parse_calendar(infile, outfile, start_date='', end_date='', calendar=''):
    print('Parsing Calendar file "%s"...') % infile
    df = pd.read_csv(infile)

    df['Start'] = pd.to_datetime(df['Start'])
    df['End'] = pd.to_datetime(df['End'])

    if start_date:
        df = df[df.Start >= start_date]

    if end_date:
        df = df[df.Start <= end_date]

    if calendar:
        df = df[df['Calendar'] == calendar]

    dd = (df['End'] - df['Start']).dt
    df['Duration'] = 24 * dd.days + dd.hours + dd.minutes / 60.0

    # drop all duplicates of Title, Start and End field
    df = df.drop_duplicates(subset=['Title', 'Start', 'End'])

    # sort by start time and reindex
    df = df.sort('Start').reset_index(drop=True)

    # get rid of extraneous blank lines in Description
    df.Description = df.Description.str.replace('[\r\n]+', '\n')

    #  Here we attempt to extract location info for every calendar event

    # These are the exact uppper case labels associated with most events on
    #  hub calendar in the 'Title' field.
    # First we try to match these exactly
    labels = {'GALLERY': ['OMI GALLERY', 'GALLERY', '\bOMI\b'],
              'ATRIUM': ['ATRIUM'],
              'BROADWAY': ['ON BROADWAY', 'BROADWAY ROOM', 'MAIN STAGE',
                           'MAIN FLOOR', 'MAIN SPACE', 'BROADWAY'],
              'JINGLETOWN': ['JINGLETOWN LOUNGE', 'JINGLETOWN'],
              'MERIDIAN': ['MERIDIAN ROOM', 'meri?di?an(?! university)'],
              'DOWNTOWN': ['DOWNTOWN'],
              'UPTOWN': ['UPTOWN'],
              'WEST_OAK': ['WEST OAKLAND', 'WEST[ |-]?OAK'],
              'EAST_OAK': ['EAST OAKLAND', 'EAST[ |-]?OAK'],
              'KITCHEN': ['KITCHEN', 'Sexy Salad'],
              'MEDITATION': ['MEDITATION ROOM'],
              'CORNER': ['CORNER OFFICE'],
              'ENTIRE': ['ENTIRE SPACE', 'WHOLE SPACE'],
              'CLOSED': ['CLOSED FOR RENTAL', 'CLOSED',
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
        print('***** ' + sup_label + ' *****')
        for label in labels[sup_label]:
            print('Title/Where text containing %s:') % label
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
            print(
                '{} records contain {} in Title/Where'
                .format(text_contains_label.sum(), label))
        print(
            '***** {} records contain {} in Title/Where *****'
            .format(df[sup_label].sum(), sup_label))

    # Check Description field for cancellations
    Description_contains_cancelled = (df.Description
                                      .str
                                      .contains('cancelled',
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
        print('"%s" contains %s') % (text[idx], guessed_label)

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
        df2.to_csv(outfile, ignore_index=True)
        print('...Wrote "%s"') % outfile

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


def label_point(x, y, val, ax):
    a = pd.concat({'x': x, 'y': y, 'val': val}, axis=1)
    for i, point in a.iterrows():
        ax.text(point['x'], point['y'], str(point['val']))


def fuzzycompare(s1, s2, thresh=False):
    c = {}
    c['ratio'] = fuzz.ratio(s1, s2)
    c['partial_ratio'] = fuzz.partial_ratio(s1, s2)
    c['token_sort_ratio'] = fuzz.token_sort_ratio(s1, s2)
    c['token_set_ratio'] = fuzz.token_set_ratio(s1, s2)
    if thresh:
        return max(c.values()) >= thresh
    else:
        return max(c.values())


# ****************************************************************************
# """
parse_calendar('HUB_cal_All.csv', 'classified_loc.csv',
               start_date='2/2014',
               calendar='Conference Room')

df = import_parsed_csv('classified_loc.csv')


df.Description = df.Description.str.replace('[\r\n]+', '\n')
df2 = df[df.Status.isnull()]
n = len(df2)

#  **** Now we determine rates for room rental

# hourly rates for non-member, part-time, and full-time renters
rate_lookup = pd.DataFrame(
    {
        'DOWNTOWN': [65, 45, 25, 0],
        'UPTOWN': [85, 65, 40, 0],
        'MERIDIAN': [95, 70, 45, 0],
        'EAST_OAK': [35, 25, 15, 0],
        'WEST_OAK': [0, 0, 0, 0],

        'GALLERY': [115, 85, 60, 0],
        'BROADWAY': [295, 225, 180, 0],
        'ATRIUM': [195, 150, 110, 0],
        'JINGLETOWN': [150, 115, 75, 0],

        'MEDITATION': [0, 0, 0, 0],
        'KITCHEN': [0, 0, 0, 0]
    },
    index=['nonmember', 'parttime', 'fulltime', 'free'])

# For title search
org_status = {
     'set[ -]?up|konda|km|simka|ashara|Dakara?i|maiki|Mikayla|zakiya|Lisa|calgary|staff|interview|HUB Oak|founders': 'free',

      'Healthy Hub|impact survey|Orientation|Conf call|Mani Niall': 'free',
      'Ayanna Davis': 'free',
      'Co[ -]?Fed': 'free',
      'balle': 'fulltime',
      'Hylo': 'fulltime',
      'Black Girls Code|BGC': 'fulltime',
      'SustainAbility': 'fulltime',
      'fedor': 'parttime',
      'New Mothers.? Circ?le': 'parttime',
      'Kapor': 'fulltime',
      'meri?di?an (?:university|staff)|rob gall': 'free',
      '[IL]v[IL] Analytics': 'fulltime',
      'Hack The Hood|Social Enterprise Course': 'fulltime',
      'uptima': 'fulltime',
      'BGC': 'fulltime',
      'SELC': 'fulltime',
      'Amigos de las Americas': 'fulltime',
      'Fund Good Jobs': 'fulltime',
      'fertl': 'fulltime',
      'Gobee': 'fulltime',
      'Jesse Posner': 'fulltime',
      'Leola Group': 'fulltime',
      'feu?ng shui': 'fulltime',
      'lingonautics': 'fulltime',
      'oakland chamber': 'nonmember',
      'Borrego Solar Systems': 'nonmember',
      'OBI Probiotic Soda': 'nonmember',
      'Factory Farming Awareness Coalition': 'nonmember',
      'Brown Sugar Kitchen': 'parttime',
      'Margo Prado|Rachel Buddaberg|Rachel Newell|Ruth Stroup|Bruce Rinehart': 'parttime',
      'HCEB': 'nonmember',
      'Joseph Huayllasco|Marianne Manilov|David Meader|Lisa Colvin|Emma Smith': 'fulltime',
      'Gil Friend|Frieda McAlear': 'nonmember',
      'Emotional Self[- ]?Defense': 'parttime',
      'Beyond Culture of Separation': 'fulltime',
      'Founding Family': 'fulltime',
      'U LAB': 'free',
      'natural flow': 'free',
      'breema': 'free',
      'sweet ?bar': 'free',
      'blue bottle': 'parttime',
      'Empower You|CompassPoint|WEAD|ZeroDivide|ACORN': 'nonmember',
      'The Shift': 'free',
      'mastermind': 'free',
      'Radical Listener': 'free',
      'Alameda County Office': 'parttime',
      'Spirits? Society': 'free',
      'iho': 'free',
      'work[ -]?trade': 'free',
      'first friday': 'free',
      'youth hub': 'free',
      'event set[ -]?up': 'free',
      'bay bucks': 'free',
      'Sungevity Party': 'free',
      'annual reviews|data meeting': 'free'
}


T = df2[['Start', Event_Location_Label, 'Title', 'Description']]


print('\nDetermining rates/income for {} records...'.format(n))

# Extract records indicating no fee in description
free = (T
        .Description
        .str
        .contains('gratis|no.charge|\$0|no cost|iho[^m]*me?e?ti?n?g',
                  case=False, na=False))

df.loc[free[free].index, 'Rate'] = 0
T = T.loc[~free]
print('...{} records explicitly labeled "no-charge" in Description'
      .format(free.sum()))


# Extract rates by matching $x/hr, $x/hour, $x per hour, etc in description
rates1 = (T
          .Description
          .str
          .extract('\$(\d+).{0,3}(?:/|per| ) ?ho?u?r', flags=re.IGNORECASE)
          .dropna()
          .astype(float))

df.loc[rates1.index, 'Rate'] = rates1
print('...{} records descriptions explicitly labeled "()/hr" or "()/hour"'
      .format(rates1.count()))

# print rates1
T = T.drop(rates1.index)

rates2 = (T.Description
          .str.extract('\$(\d+) x ', flags=re.IGNORECASE)
          .dropna()
          .astype(float))

df.loc[rates2.index, 'Rate'] = rates2
print('...{} records descriptions explicitly labeled "$() x "'
      .format(rates2.count()))

# print rates2
T = T.drop(rates2.index)

rates3 = (T
          .Description
          .str.extract(' x \$(\d+)', flags=re.IGNORECASE)
          .dropna()
          .astype(float))

df.loc[rates3.index, 'Rate'] = rates3
print('...{} records descriptions explicitly labeled " x $()"'
      .format(rates3.count()))

T = T.drop(rates3.index)


# Extract rates from remaining records that specify renter class in description
desc_keywords = {'Non[ -]?member': 'nonmember',
                 'part[ -]?time': 'parttime'}
for kw in desc_keywords.keys():
    contains_kw = T.Description.str.contains(kw, na=False, case=False)
    room = df[Event_Location_Label][contains_kw[contains_kw].index].dropna()
    rates = room.apply(lambda x: rate_lookup[x][desc_keywords[kw]])
    df.loc[rates.index, 'Rate'] = rates
    print('\n...{} descriptions containing "{}", which has "{}" status'
          .format(rates.count(), kw, desc_keywords[kw]))
    print(df.loc[rates.index, ['Title', 'Rate']])
    T = T.drop(rates.index)


# Extract rates by organization name in Title
for org in org_status.keys():
    contains_org = T.Title.str.contains(org, na=False, case=False)
    room = df[Event_Location_Label][contains_org[contains_org].index].dropna()
    rates = room.apply(lambda x: rate_lookup[x][org_status[org]])
    df.loc[rates.index, 'Rate'] = rates
    print('\n...{} titles containing "{}", which has "{}" status'
          .format(rates.count(), org, org_status[org]))

    print(df.loc[rates.index, ['Title', 'Rate']])
    T = T.drop(rates.index)


tfs = T.Title.str.contains('future sound', case=False, na=False)
tfs = tfs[tfs]
df.loc[tfs.index, 'Rate'] = 18
print('\n...{} Titles contain "future sound" which gets a rate of $18'
      .format(tfs.count()))

T = T.drop(tfs.index)


df.loc[:, 'Charge'] = df.Duration * df.Rate

# find explicitly recorded total charge values
total = (T
         .Description
         .str
         .extract('(?:total|charging|charge|price|paid)[^$]*\$(\d+)',
                  flags=re.IGNORECASE)
         .dropna())

df.loc[total.index, 'Charge'] = total
T = T.drop(total.index)
print('\n...{} Descriptions contain explicit total charge'
      .format(total.count()))

# Whatever record descriptions have $ in them we will go ahead and call
# those total amounts
total2 = T.Description.str.extract('\$(\d+)', flags=re.IGNORECASE).dropna()
df.loc[total2.index, 'Charge'] = total2
print('\n...{} Descriptions contain implicit total charge'
      .format(total2.count()))
print(total2)
T = T.drop(total2.index)

#totals_without_rates = df.Charge.notnull() & df.Rate.isnull()
# df.Rate[totals_without_rates] = (df.Charge[totals_without_rates] /
#                                  df.Duration[totals_without_rates])

# Finally we manually update classification with fixes from Tatiana's fix-file
T_unc = T[T.Loc.isin(conf_rooms)]
T_fix = pd.read_csv('unclassified_records_fixes.csv')

for idx, row in T_fix.dropna(subset=['Title']).iterrows():
    contains_fix = T_unc.Title.str.contains(row.Title, na=False, case=False)
    if any(contains_fix):
        T_unc.loc[contains_fix, 'Level'] = row.Level

# T_unc[['Start','Title','Level','Description']].to_csv('unclassified_records.csv')

T_unc_free = T_unc[T_unc.Level == 'free']
df.loc[T_unc_free.index, 'Rate'] = 0

T_unc_pt = T_unc[T_unc.Level == 'part-time']
rates = T_unc_pt.Loc.apply(lambda x: rate_lookup[x]['parttime'])
df.loc[rates.index, 'Rate'] = rates

T_unc_ft = T_unc[T_unc.Level == 'full-time']
rates = T_unc_ft.Loc.apply(lambda x: rate_lookup[x]['fulltime'])
df.loc[rates.index, 'Rate'] = rates

T_unc_nm = T_unc[T_unc.Level == 'non-member']
rates = T_unc_nm.Loc.apply(lambda x: rate_lookup[x]['nonmember'])
df.loc[rates.index, 'Rate'] = rates

T_unc_delete = T_unc[T_unc.Level == 'delete']
df.loc[rates.index, 'Status'] = 'CLOSED'

to_update = df.Charge.isnull() & df.Rate.notnull()
df.Charge[to_update] = df.Rate[to_update] * df.Duration[to_update]


df.Charge = df.Charge.astype(float)
df2 = df[df.Status.isnull() & (df.Start >= '3/2014')].drop('Status', axis=1)
df2[['Start', 'Loc', 'Duration', 'Rate', 'Charge', 'Title', 'Description']
    ].to_csv('classified_loc_charge.csv')
#"""

df2 = import_parsed_csv('classified_loc_charge.csv')
bk = (df2[['Start', 'Rate',
           'Duration', 'Charge',
           Event_Location_Label]]
      .dropna(subset=[Event_Location_Label, 'Charge']))


drange = '03-26-2014 to 05-12-2015'


#  *** Output Reports ***

# pv is the data structure we want
pv = pd.pivot_table(bk,
                    columns=Event_Location_Label,
                    index='Start',
                    values='Duration',
                    aggfunc=pd.np.sum)

hours_by_month = pv[conf_rooms].resample('M', how='sum').fillna(0)
ax = hours_by_month.plot(figsize=(15, 5), title='Hours over ' + drange)
hours_by_month.plot(style='o', ax=ax, legend=False)
# print hours_by_month

bookings_by_month = pv[conf_rooms].resample('M', how='count').fillna(0)
ax = bookings_by_month.plot(figsize=(15, 5), title='Count over ' + drange)
bookings_by_month.plot(style='o', ax=ax, legend=False)
# print bookings_by_month

pv = pd.pivot_table(bk,
                    columns=Event_Location_Label,
                    index='Start',
                    values='Charge',
                    aggfunc=pd.np.sum)

income_by_month = pv[conf_rooms].fillna(0).resample('M', how='sum')
ax = income_by_month.plot(
    figsize=(15, 5), title='\$ Dollars \$ over ' + drange)
income_by_month.plot(style='o', ax=ax, legend=False)
# print income_by_month


pv = pd.pivot_table(bk,
                    index='Rate',
                    columns='Loc',
                    values='Duration',
                    aggfunc=pd.np.sum)[conf_rooms]
pv_adj = pv / pv.sum()

for room in conf_rooms:
    plt.figure()
    pv_adj[room].dropna().plot(
        kind='bar',
        title=room + ': Rate distribution over ' + drange,
        figsize=(12, 5))


pv = pd.pivot_table(bk,
                    index='Rate',
                    columns='Loc',
                    values='Charge',
                    aggfunc=pd.np.sum)[conf_rooms]
plt.figure()
pv.sum().plot(kind='bar', title='Total \$ over ' + drange, figsize=(12, 5))


pv = pd.pivot_table(bk,
                    index='Rate',
                    columns='Loc',
                    values='Duration',
                    aggfunc=pd.np.sum)[conf_rooms]
plt.figure()
pv.sum().plot(kind='bar',
              title='Total rented hours ' + drange, figsize=(12, 5))


pv = pd.pivot_table(bk,
                    index='Rate',
                    columns='Loc',
                    values='Duration',
                    aggfunc=lambda x: x.count())[conf_rooms]
plt.figure()
pv.sum().plot(kind='bar',
              title='Total times rented ' + drange,
              figsize=(12, 5))
