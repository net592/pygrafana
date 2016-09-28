# pygrafana
Grafana dashboard builder and HTTP API interface for Python

# Motivation
I wanted to script grafana dashboards based on entries in the time-series database. Long time I changed the json documents directly but with increasing complexity this was not feasible anymore. The current version wraps almost anything in classes that can be put together to a dashboard.

In order to update the dashboards in Grafana and to do some manangements stuff, I added an interface to the HTTP API. I tested the API interface with Grafana 2.1.3.

# Current classes
- Target
- Tooltip
- Legend
- Grid
- Panel
- TextPanel (inherited from Panel)
- PlotPanel (inherited from Panel)
- SeriesOverride
- Graph (inherited from PlotPanel)
- Gauge
- Sparkline
- SingleStat (inherited from PlotPanel)
- Row
- Template
- Timepicker
- Dashboard

Almost all class options can be set at init but also afterwards by `set_<option>()` functions. Each class has a `get()` function to return the current content as a Python dictionary. With `get_json()` you can get the json document of a class.

I use InfluxDB as backend for Grafana. Therefore, I don't know whether the Target class fits for other backends. I will test the others as soon as I have time.

# Example
```
from pygrafana.dashboard import Target, Graph, Row, Dashboard
from pygrafana.api import Connection

# Create a database query target
t = Target("testmetric", alias="Testmetric [[tag_host]]")
# Add a Tag to the query target
t.add_tag("host", "$hostname", operator="=~") # automatically adds '/' when operator uses regex
# Create a graph panel displaying the single Target
g = Graph(targets=[t])
# Create a row for the graph panel
r = Row("Testmetric Row")
# Add the graph panel to the row
r.add_panel(g)
# Create a dashboard
d = Dashboard("Test Dashboard")
# Add row
d.add_row(r)
# sets datasource of all targets and templates in dashboard
d.set_datasource("myDS") 
# Get JSON of dashboard
res = d.get_json() 
# Get dict of dashboard
res = d.get()
# Establish connection to Grafana
con = Connection("localhost", 3000, "testuser", "testpass")
# Add dashboards tags JSON documents or Dashboard objects
print con.add_dashboard(d)
```
