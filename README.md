# pygrafana
Dashboard builder for python

# Motivation
I wanted to script grafana dashboards based on entries in the time-series database. Long time I changed the json documents directly but with increasing complexity this was not feasible anymore. The current version wraps almost anything in classes that can be put together to a dashboard.

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

# Example
```
t = Target("testmetric", alias="Testmetric [[tag_host]]")
t.add_tag("host", "$hostname", operator="=~") # automatically adds '/' when operator uses regex
g = Graph(targets=[t])
r = Row("Testmetric Row")
r.add_panel(g)
d = Dashboard("Test Dashboard")
d.add_row(r)
d.set_datasource("myDS") # sets datasource of all targets and templates in Dashboard
# Get JSON of dashboard
res = d.get_json() 
# Get dict of dashboard
res = d.get()
