## Note: Use <lsof -ti tcp:8050 | xargs kill -9> after running the app to kill its process ##

import plotly.graph_objects as go # or plotly.express as px
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import numpy as np
import dash_table
import utils
from datetime import datetime
import json
from os import path, environ


colors = {
    'background': '##333',
    'text': '#7FDBFF'
}
    

# Preprocessing Data
data = pd.read_csv("https://www.fire.ca.gov/imapdata/mapdataall.csv")
data=data[data['incident_acres_burned'].notnull()] # Dropping Nulls
data=data[data['incident_dateonly_extinguished'].notnull()] # Dropping Nulls
data['date'] = pd.to_datetime(data['incident_dateonly_extinguished'])
data = data[data.date >  datetime.strptime('2010-01-01', '%Y-%m-%d')] # Dropping wrong/invalid dates


min_date = min(data.date)
max_date = max(data.date)

navbar = html.Div(className='topnav' ,children=[
        html.A('Home', className="home-page", href='home'),
        html.A('California Incident Map', className="cali-map", href='app1'),
        html.A('County Incident Map', className="county-map", href='app2'), 
        html.A('Prediction', className="pred", href='app3')
])

date_picker_widget = dcc.DatePickerRange(
        id='date_picker',
        min_date_allowed=min_date,
        max_date_allowed=max_date,
        start_date=min_date,
        end_date=max_date,
        number_of_months_shown=6, 
    )


# Map Widget
if path.exists('.mapbox_token'):
    px.set_mapbox_access_token(open(".mapbox_token").read())
elif environ['mapbox_token']:
    px.set_mapbox_access_token(environ['mapbox_token'])


cali_map = dcc.Graph(id='cali_map')
county_map = dcc.Graph(id='county_map')
county_pie = dcc.Graph(id='county_pie')


# Building App Layout
app = dash.Dash(__name__)
header = html.Div(style={'backgroundColor':colors['background']} ,children=[
        html.H1(children='California Wildfire Interactive Dashboard'),
    ])
county_map_div = html.Div(style={'border':'2px black solid', 'padding': '10px'}, children=county_map)
county_pie_div = html.Div(style={'border':'2px black solid', 'padding': '10px'}, children=county_pie)

date_picker_row = html.Div(style={'textAlign': 'center', 'padding': '4px'}, children=[html.Div(children='Filter by Date:'), date_picker_widget])

table_columns = ['incident_name' ,'incident_administrative_unit', 'incident_location']
cali_map_table = dash_table.DataTable(
    style_table={
        'height': 500,
        'overflowY': 'scroll',
        'width': 540
    },
    id='table',
    style_header={'backgroundColor': '#04AA6D'},
    style_cell={
        'backgroundColor': 'rgb(50, 50, 50)',
        'color': 'white'
    },
    columns=[{"name": i, "id": i} for i in table_columns],
    data=data[["incident_name", "incident_administrative_unit", "incident_location"]].to_dict('record'),
)

cali_map_div = html.Div(id = 'cal-map',style={'border':'2px black solid', 'padding': '10px', 'columnCount': 2}, children=[cali_map,  html.Div(style={'padding':'150px'},children=[cali_map_table])])
second_row = html.Div(style={'columnCount': 2}, children=[county_map_div, county_pie_div])
app.title = 'Cal Wildfire Dashboard'

app.layout = html.Div(style={'border':'2px black solid'},children=[dcc.Location(id='url', refresh=False), header, navbar, html.Div(id='page-content')])

# county-map callbacks
@app.callback(
    dash.dependencies.Output('table', 'data'),
    [dash.dependencies.Input('cali_map', 'selectedData')])
def display_data(selectedData):
    table_data =  pd.DataFrame()
    # print(type(selectedData))
    # print(selectedData)
    if not selectedData:
        return table_data.to_dict('records')

    returnStr = ''
    for pt in selectedData['points']:
        row = data.loc[(data['incident_longitude'] == pt['lon']) & (data['incident_latitude'] == pt['lat'])]
        table_data = table_data.append(row)
        returnStr += f"{pt['hovertext']} - Size: TODO, Location: ({pt['lon']:.2f}, {pt['lat']:.2f})\n"
    table_data = table_data[["incident_name", "incident_administrative_unit", "incident_location"]]
    table_data = table_data.to_dict('records')
    print(table_data)
    return table_data
    

@app.callback(
    dash.dependencies.Output('cali_map', 'figure'),
    [dash.dependencies.Input('date_picker', 'start_date'), dash.dependencies.Input('date_picker', 'end_date')])
def update_cali_map(start_date, end_date):
    fig = px.scatter_mapbox(
        data[(data.date >= start_date) & (data.date <= end_date)], lat="incident_latitude", lon="incident_longitude", size='incident_acres_burned', 
        zoom=4, height=500, width=850, size_max=22,  hover_name="incident_name", hover_data=["incident_county"], 
        color_discrete_sequence=['red'], center={'lon':-119.66673872628975, 'lat':37.219306366090116}, title='Wildfires Incident Map',
    )

    fig.update_layout(margin={"r":0,"t":25,"l":0,"b":0})
    fig.update_layout(
        autosize=True,
        hovermode='closest',
        showlegend=True,
    ) 

    return fig


# county-map callbacks
@app.callback(
    dash.dependencies.Output('county_map', 'figure'),
    [dash.dependencies.Input('date_picker', 'start_date'), dash.dependencies.Input('date_picker', 'end_date')])
def update_county_map(start_date, end_date):
    county_map_fig = px.choropleth(
        utils.getCountyNumbersDF(data, start_date, end_date), geojson=utils.counties, locations='county', 
        color='Number of County Incidents', featureidkey='properties.name', projection="mercator", 
        color_continuous_scale=px.colors.sequential.Reds, center={'lon':-119.66673872628975, 'lat':37.219306366090116}, title='County Incident Frequency', 
        width=800, height=800
    )

    county_map_fig.update_geos(fitbounds='geojson', visible=False)
    county_map_fig.update_layout(margin={"r":0,"t":25,"l":0,"b":0})

    return county_map_fig

@app.callback(
    dash.dependencies.Output('county_pie', 'figure'),
    [dash.dependencies.Input('date_picker', 'start_date'), dash.dependencies.Input('date_picker', 'end_date')])
def update_county_pie(start_date, end_date):
    county_pie_fig = px.pie(
        utils.getCountyNumbersDF(data, start_date, end_date), values='Number of County Incidents', names='county', 
        width=800, height=800, title='County Incident Distribution'
    )

    county_pie_fig.update_layout(margin={"r":0,"t":25,"l":0,"b":0})

    return county_pie_fig



# Navbar callback
@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    print(pathname)
    if pathname == '/home':
        return html.Div()
    elif pathname == '/app1':
        return html.Div(children=[date_picker_row, cali_map_div])
    elif pathname == '/app2':
        return html.Div(children=[date_picker_row, second_row])
    elif pathname == '/app3':
        return html.Div()

if __name__ == '__main__':
    #Running App (Port 8050 by default)
    app.run_server(host='0.0.0.0', debug=True, use_reloader=False, dev_tools_ui=False)  # Turn off reloader if inside Jupyter

## Note: Use <lsof -ti tcp:8050 | xargs kill -9> after running the app to kill its process ##