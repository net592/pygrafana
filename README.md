# pygrafana
[Grafana](http://grafana.org/) dashboard builder and HTTP API interface for Python

# Motivation
I wanted to script Grafana dashboards based on entries in the time-series database. Long time I changed the JSON documents directly but with increasing complexity this was not feasible anymore. The current version wraps almost anything in classes that can be put together to a dashboard.

In order to update the dashboards in Grafana and to do manangement stuff, I added an interface to the HTTP API. The interface should provide all documented API features. I also added some additional functions for e.g. API call that exist for ID but not for name.


I tested the API interface and the dashboard builder with Grafana 2.1.3 and 3.1.1. It was originally written for 2.1.3. With the support for 3.x.x the classes do not fit the output JSON to 100% anymore. An example would be the Grid class for y axes limits which moved to the panels in 3.x.x. The changes are handled internally, you still have to use the Grid class for 3.x.x.

For communication with Grafana, the module uses the [Requests](http://de.python-requests.org/de/latest/) module if available. If not, it fallbacks to urllib2 with an extension to send other requrests than GET and POST.

# Current classes
- Target
- Tooltip
- Legend
- Grid
- Panel
- TextPanel (inherited from Panel)
- PlotPanel (inherited from Panel)
- SeriesOverride
- GraphPanel (inherited from PlotPanel)
- Gauge
- Sparkline
- SingleStat (inherited from PlotPanel)
- PiePanel (+)
- Row
- Template
- Timepicker
- Dashboard

(+) The PiePanel is only available with Grafana 3.1.1

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
g = GraphPanel(targets=[t])
# use set functions to enable transparency
g.set_transparent(True)
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
