#!/usr/bin/python

from pygrafana import *

# Create a target for testmetric
t = Target("testmetric")
# Set alias, same Target("testmetric", alias="Testmetric [[tag_host]]")
t.set_alias("Testmetric [[tag_host]]")
# Add a tag
t.add_tag("host", "$hostname", operator="=~")
# Group measurements by tag 'host'
t.add_groupBy("tag", "host")

# Create Graph panel
g = Graph()
# Add testmetric target to graph
g.add_target(t)

# Create a SingleStat panel
b = SingleStat()
# Add testmetric target to singlestat
b.add_target(t)

# Create a rows and add graph and singlestat
r = Row()
r.add_panel(g)
r.add_panel(b)

# Create a template to filter later. tags are appended to selection query
te = Template("hostname", "host", tags=[("jobid", "1234.tbadm")])

# Finally create a dashboard
d = Dashboard("Test")
# add the row
d.add_row(r)
# add template
d.add_template(te)
# set datasource for all targets and templates in dashboard
d.set_datasource("myDS")
# set refresh interval
d.set_refresh("10s")

# get json
print d.get_json()
# get dictionary
print d.get()
