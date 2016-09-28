#!/usr/bin/python

import copy
import json
import re

# s (seconds), m (minutes), h (hours), d (days), w (weeks), M (months), y (years
time_limits = { "s" : 60, "m" : 60, "h" : 24, "d" : 31, "w": 52, "M" : 12, "y" : 100}
def check_timerange(t):
    """
    Checks a timerange string for validity
    
    Checks if string is anything like now-1h, or now-6h/h up to a date like 2016-09-17 04:31:00
    
    :param t: timerange string
    :return True/False
    """
    if isinstance(t, str):
        if time == "now":
            return True
        if "now" in t:
            m = re.match("now[-]([\d]+[smhdwMy])$")
            if m:
                return True
            m = re.match("now[-]([\d]+)([smhdwMy])/[smhdwMy]$")
            if m and len(m.groups) == 2:
                val, sym = m.groups()
                if int(val) > 0 and int(val) < time_limits[sym]:
                    return True
                else:
                    print "out of range"
                    return False
        m = re.match("([\d][\d][\d][\d])-([\d][\d])-([\d][\d]) ([\d][\d]):([\d][\d]):([\d][\d])")
        if m:
            return True
    return False

def check_color(c):
    """
    Checks a color string or tuple with numeric values
    
    :param c: Color string or tuple
    :return c or None
    """
    if isinstance(c, str):
        m = re.match("rgba\((\d+),\s*(\d+),\s*(\d+),\s*(0.[\d]+)\)", c)
        if m and int(m.group(1)) < 255 and int(m.group(2)) < 255 and int(m.group(3)) < 255 and float(m.group(4)) > 0 and float(m.group(4)) <= 1:
            return c
        m = re.match("rgb\((\d+),\s*(\d+),\s*(\d+)\)", c)
        if m and int(m.group(1)) < 255 and int(m.group(2)) < 255 and int(m.group(3)) < 255:
            return c
        m = re.match("#[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]$", c)
        if m:
            return c
    elif isinstance(c, tuple):
        if len(c) == 3 and int(c[0]) > 0 and int(c[0]) < 256 and \
                           int(c[1]) > 0 and int(c[1]) < 256 and \
                           int(c[2]) > 0 and int(c[2]) < 256:
            return "rgb(%d,%d,%d)" % (int(c[0]), int(c[1]), int(c[2]),)
        if len(c) == 4 and int(c[0]) > 0 and int(c[0]) < 256 and \
                           int(c[1]) > 0 and int(c[1]) < 256 and \
                           int(c[2]) > 0 and int(c[2]) < 256 and \
                           float(c[3]) > 0 and float(c[3]) < 1:
            return "rgba(%d,%d,%d, %f)" % (int(c[0]), int(c[1]), int(c[2]), float(c[3]),)
    return None

target_id = 0

class Target(object):
    """
    Encapsulates an query and evaluation target used in Grafana's panels
    """
    def __init__(self, measurement, dsType="influxdb", alias="", tags=[],
                  groupBy=[], select=[], query="", resultFormat="time_series"):
        """
        Construct a new Target object
        
        :param measurement: The name of the measurement
        :param dsType: String with the identifier for a supported data source
        :param alias: Alias in the panel's legend for this target
        :param tags: List of tags (Format: {{'key': DB key as string, 'value': DB value as string, 'operator': any valid operator as string, 'condition': any valid conditon as string})
        :param groupBy: List of grouping options (Format: {'type': any of ('fill', 'time', 'tag'), 'params': [parameter(s) for type, e.g. tag name]})
        :param select: Which elements in a measurement should be returned and further processed. (Format: {'type': 'field' or any valid function, 'params': [parameter(s) for type, e.g. 'value' if type == 'field' or function argument]})
        :param query: Query that is send to the data source. Not required for InfluxDB but probably the Graphite query is in here.
        :param resultFormat: Currently the only supported option is 'time_series'. There are others but not implemented yet.
        """
        self.dsType = dsType
        self.tags = tags
        self.groupBy = groupBy
        self.alias = alias
        self.select = select
        self.measurement = measurement
        self.query = query
        global target_id
        self.refId = target_id
        target_id += 1
        self.resultFormat = resultFormat
        self.validGroupBy = ['fill', 'time', 'tag']
        self.validResultFormat = ["time_series"]
    def get(self):
        """
        Returns a dictionary with the Target object's configuration. Performs some sanitation like removing duplicated groupBy options
        and creates a valid query for InfluxDB based on the configuration.
        
        :return dict with the Target object's settings
        """
        t = None
        t = {}
        t["dsType"] = self.dsType
        t["tags"] = self.tags
        t["groupBy"] = self.groupBy
        t["alias"] = self.alias
        t["select"] = self.select
        t["measurement"] = self.measurement
        t["query"] = self.query
        t["refId"] = self.refId
        t["resultFormat"] = self.resultFormat
        grp_has_time = False
        grp_has_fill = False
        for g in self.groupBy:
            if g["type"] == "time":
                grp_has_time = True
            elif g["type"] == "fill":
                grp_has_fill = True
        if not grp_has_time:
            t["groupBy"].append({'type': 'time', 'params': ['$interval']})
        if not grp_has_fill:
            t["groupBy"].append({'type': 'fill', 'params': ['null']})
        has_field = False
        has_func = False
        for s in self.select:
            if s["type"] == "field":
                has_field = True
            if s["type"] != "field":
                has_func = True
        if not has_field:
            t["select"].append({ "params": [ "value" ], "type": "field" })
        if not has_func:
            t["select"].append({ "params": [], "type": "mean" })
        if len(self.query) == 0:
            field = "value"
            func = "mean"
            func_params = ""
            for s in t["select"]:
                if s["type"] == "field":
                    field = ",".join(s["params"])
                else:
                    func = s["type"]
                    if len(s["params"]) > 0:
                        func_params = "," + ",".join(s["params"])
            t["query"] = "SELECT %s (\\\"%s\\\"%s) FROM \\\"%s\\\" WHERE $timeFilter" % (func, field, func_params, self.measurement,)
            filt = ""
            for s in t["tags"]:
                op = s["operator"]
                val = s["value"]
                key = s["key"]
                
                if val[0] == "$" and val[-1] != "$":
                    val += "$"
                
                if op in ["=~", "!~"]:
                    if val[0] != "/":
                        val = "/"+val
                    if val[-1] != "/":
                        val += "/"
                if s.has_key("condition"):
                    filt += "%s %s %s %s " % (s["condition"], key, op, val,)
                else:
                    filt += "%s %s %s " % (key, op, val,)
            
            if len(filt) > 0:
                t["query"] += " AND %s" % (filt,)
        
        return t
    def get_json(self):
        """
        Returns a JSON string with the Target object's configuration.
        
        :return JSON string with the Target object's settings
        """
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        t = self.get()
        s = "Target(%s, dsType=\"%s\", alias=\"%s\", " % (t.measurement, t.dsType, t.alias,)
        
        s += "tags=[%s], " % (", ".join([str(a) for a in t.tags]),)
        s += "groupBy=[%s], " % (", ".join([str(g) for g in t.groupBy]),)
        s += "select=[%s], " % (", ".join([str(s) for s in t.select]),)
        s += "query=\"%s\", resultFormat=\"%s\"" % (t.query, t.resultFormat,)
        return s
    def set_dsType(self, dsType):
        """
        Set data source type.
        
        :param dsType: Valid identifier string for Grafana data source types. Currently no validity checks
        :return True/False
        """
        if not isinstance(dsType, str):
            try:
                dsType = str(dsType)
            except ValueError:
                return False
        self.dsType = dsType
        return True
    def set_refId(self, refId):
        """
        Set reference identifier (refId).
        
        :param refId: Reference identifier string(!) like 'A','B'
        :return True/False
        """
        if not isinstance(refId, str):
            try:
                refId = str(refId)
            except ValueError:
                return False
        self.refId = refId
        return True
    def set_alias(self, alias):
        """
        Set alias for this Target in panel's legend.
        
        TODO: Warn if alias contains [[tag_<tagname>]] but no valid entry in groupBy exists
        
        :param alias: Alias for this Target
        :return True/False
        """
        if not isinstance(alias, str):
            try:
                alias = str(alias)
            except ValueError:
                return False
        self.alias = alias
        return True
    def set_resultFormat(self, fmt):
        """
        Set result format for this Target.
        
        TODO: Add missing valid result formats
        
        :param fmt: Result format. Currently only "time_series" allowed
        :return True/False
        """
        if fmt in self.validResultFormat:
            self.resultFormat = fmt
            return True
        return False
    def add_tag(self, key, value, operator='=', condition='AND'):
        """
        Add a tag to this target.
        Performs some sanitation by adding missing trailing $ for dashboard tags or add missing / around the value if operator is a regex operator.
        
        :param key: DB key
        :param value: DB value
        :param operator: A valid operator like '=' or '=~'
        :param condition: A valid condition like 'AND' or 'OR'
        :return True/False
        """
        try:
            val = value
            if val[0] == "$" and val[-1] != "$":
                val += "$"
            
            if operator in ["=~", "!~"]:
                if val[0] != "/":
                    val = "/"+val
                if val[-1] != "/":
                    val += "/"
            if len(self.tags) == 0:
                tag = {'key': key, 'value': val, 'operator': operator}
            else:
                tag = {'key': key, 'value': val, 'operator': operator, 'condition': condition}
            self.tags.append(tag)
            return True
        except:
            pass
        return False
    def add_select(self, sel_type, sel_params):
        """
        Add a select configuration for this Target. Duplicated additions are discarded
        
        :param sel_type: Type of select like 'field' or any valid function
        :param sel_params: Parameters of select like 'value' for 'field' or function arguments. If parameter is not a list, the parameter is put in one.
        :return True/False
        """
        if not isinstance(sel_type, list):
            sel_type = [sel_type]
        s = { "params": sel_params, "type": sel_type }
        if not s in select:
            self.select.append(s)
            return True
        return False
    def add_groupBy(self, grp_type, grp_params):
        """
        Add a groupBy configuration for this Target. Duplicated additions are discarded
        
        :param sel_type: Type of groupBy options. Valid types are 'fill', 'time' and 'tag'.
        :param sel_params: Parameter to the groupBy type. 
        :return True/False
        """
        if grp_type not in self.validGroupBy:
            return False
        if grp_type != 'tag':
            for g in self.groupBy:
                if g["type"] == grp_type:
                    g["params"] = grp_params
                    return True
        d = {'type': grp_type, 'params': grp_params}
        if d not in self.groupBy:
            self.groupBy.append(d)
            return True
        return False
    def read_json(self, j):
        """
        Configure Target object according to settings in JSON document describing a Target
        
        :param sel_type: Type of groupBy options. Valid types are 'fill', 'time' and 'tag'.
        :param sel_params: Parameter to the groupBy type. 
        :return True/False
        """
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("resultFormat"):
            self.set_resultFormat(j["resultFormat"])
        if j.has_key("alias"):
            self.set_alias(j["alias"])
        if j.has_key("refId"):
            self.set_refId(j["refId"])
        if j.has_key("dsType"):
            self.set_dsType(j["dsType"])
        if j.has_key("query"):
            self.query = j["query"]
        if j.has_key("measurement"):
            self.measurement = j["measurement"]
        if j.has_key("tags"):
            if isinstance(j["tags"], list):
                for t in j["tags"]:
                    key = None
                    value = None
                    operator = "="
                    if t.has_key("key") and t.has_key("value"):
                        key = t["key"]
                        value = t["value"]
                    else:
                        print "Invalid tag %s, Format is {'key': '', 'value': '', 'operator': '', 'condition': ''}" % str(t)
                        continue
                    if t.has_key("operator"):
                        operator = t["operator"]
                    if t.has_key("condition"):
                        self.add_tag(key, value, operator=operator, condition=t["condition"])
                    else:
                        self.add_tag(key, value, operator=operator)
        if f.has_key("groupBy"):
            if isinstance(j["groupBy"], list):
                for gb in j["groupBy"]:
                    t = None
                    p = None
                    if gb.has_key("type"):
                        t = gb["type"]
                    if gb.has_key("params"):
                        p = gb["params"]
                    if not t or not p:
                        print "Invalid groupBy JSON %s, Format is {'type': '', 'params': []}" % str(gb)
                        continue
                    if not isinstance(p, list):
                        print "Invalid groupBy JSON %s, Format is {'type': '', 'params': []}" % str(gb)
                        continue
                    self.add_groupBy(t, p)
        if f.has_key("select"):
            if isinstance(j["select"], list):
                for sel in j["select"]:
                    t = None
                    p = None
                    if sel.has_key("type"):
                        t = gb["type"]
                    if sel.has_key("params"):
                        p = gb["params"]
                    if not t or not p:
                        print "Invalid select JSON %s, Format is {'type': '', 'params': []}" % str(sel)
                        continue
                    if not isinstance(p, list):
                        print "Invalid select JSON %s, Format is {'type': '', 'params': []}" % str(sel)
                        continue
                    self.add_select(t, p)
        

class Tooltip(object):
    """
    Encapsulates tooltip configuration used in Grafana's graph panels
    """
    def __init__(self, shared=True, value_type="cumulative"):
        self.shared = shared
        self.value_type = value_type
        self.validValueTypes = ["cumulative"]
    def set_shared(self, s):
        if isinstance(s, bool):
            self.shared = s
    def set_value_type(self, v):
        if isinstance(v, str) and v in self.validValueTypes:
            self.value_type = v
            return True
        return False
    def get(self):
        return {"shared" : self.shared, "value_type" : self.value_type}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return "Tooltip(shared=%s, value_type=\"%s\")" % (str(self.shared), self.value_type)
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("shared"):
            self.set_shared(j["shared"])
        if j.has_key("value_type"):
            self.set_value_type(j["value_type"])

class Legend(object):
    def __init__(self, total=False, show=True, max=False, min=False, current=False, values=False, avg=False):
        self.total = total
        self.show = show
        self.max = max
        self.min = min
        self.current = current
        self.values = values
        self.avg = avg
    def set_total(self, t):
        if isinstance(t, bool):
            self.total = t
    def set_show(self, s):
        if isinstance(s, bool):
            self.show = s
    def set_max(self, m):
        if isinstance(m, bool):
            self.max = m
    def set_min(self, m):
        if isinstance(m, bool):
            self.min = m
    def set_current(self, m):
        if isinstance(m, bool):
            self.current = m
    def set_values(self, m):
        if isinstance(m, bool):
            self.values = m
    def set_avg(self, m):
        if isinstance(m, bool):
            self.avg = m
    def get(self):
        return {"total" : self.total, "show" : self.show, "max" : self.max,
                "min" : self.min, "current" : self.current, "values" : self.values,
                "avg" : self.avg}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        l = "Legend(total=%s, show=%s, max=%s, " % (self.total, self.show, self.max,)
        l += "min=%s, current=%s, values=%s, avg=%s)" % (self.min, self.current, self.values, self.avg,)
        return l
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("total"):
            self.set_total(j["total"])
        if j.has_key("show"):
            self.set_show(j["show"])
        if j.has_key("max"):
            self.set_max(j["max"])
        if j.has_key("min"):
            self.set_min(j["min"])
        if j.has_key("current"):
            self.set_current(j["current"])
        if j.has_key("values"):
            self.set_values(j["values"])
        if j.has_key("avg"):
            self.set_avg(j["avg"])

class Grid(object):
    def __init__(self, leftMax=None, threshold2=None, rightLogBase=1, rightMax=None, threshold1=None,
                    leftLogBase=1, threshold2Color="rgba(234, 112, 112, 0.22)",rightMin=None,
                    threshold1Color="rgba(216, 200, 27, 0.27)", leftMin=None):
        self.leftMax = leftMax
        self.threshold2 = threshold2
        self.rightLogBase = rightLogBase
        self.rightMax = rightMax
        self.threshold1 = threshold1
        self.leftLogBase = leftLogBase
        self.threshold2Color = check_color(threshold2Color)
        self.rightMin = rightMin
        self.threshold1Color = check_color(threshold1Color)
        self.leftMin = leftMin
    def get(self):
        return {"leftMax" : self.leftMax, "threshold2" : self.threshold2,
                "rightLogBase" : self.rightLogBase, "rightMax" : self.rightMax,
                "threshold1" : self.threshold1, "leftLogBase" : self.leftLogBase,
                "threshold2Color" : self.threshold2Color, "rightMin" : self.rightMin,
                "threshold1Color" : self.threshold1Color, "leftMin" : self.leftMin}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("leftMax"):
            self.set_leftMax(j["leftMax"])
        if j.has_key("threshold2"):
            self.set_threshold2(j["threshold2"])
        if j.has_key("rightLogBase"):
            self.set_rightLogBase(j["rightLogBase"])
        if j.has_key("rightMax"):
            self.set_rightMax(j["rightMax"])
        if j.has_key("threshold1"):
            self.set_threshold1(j["threshold1"])
        if j.has_key("leftLogBase"):
            self.set_leftLogBase(j["leftLogBase"])
        if j.has_key("threshold2Color"):
            self.set_threshold2Color(j["threshold2Color"])
        if j.has_key("rightMin"):
            self.set_rightMin(j["rightMin"])
        if j.has_key("threshold1Color"):
            self.set_threshold1Color(j["threshold1Color"])
        if j.has_key("leftMin"):
            self.set_leftMin(j["leftMin"])

panel_id = 0



class Panel(object):
    def __init__(self, span=12, editable=True, title=""):
        global panel_id
        self.id = panel_id
        panel_id += 1
        self.span = span
        self.title = title
        self.editable = editable
    def set_editable(self, b):
        if isinstance(b, bool):
            self.editable = b
    def set_title(self, t):
        self.title = str(t)
    def set_span(self, b):
        if isinstance(b, int) and b in range(1,13):
            self.span = b
    def get(self):
        return {}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        pass

class TextPanel(Panel):
    def __init__(self, title="default title", mode="markdown", content="",
                       style={}, span=12, editable=True):
        Panel.__init__(self, span=span, editable=editable, title=title)
        self.set_mode(mode)
        self.content = content
        self.style = style
        self.type = 'text'
    def set_mode(self, m):
        if m in ['html', 'markdown', 'text']:
            self.mode = m
    def set_content(self, c):
        if isinstance(c, str):
            self.content = c
    def get(self):
        return {"title" : self.title, "mode" : self.mode,
                "content" : self.content, "style" : self.style,
                "span" : self.span, "editable": self.editable,
                "id": self.id}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        p = "Textpanel(title=\"%s\", mode=\"%s\", content=\"%s\", " % (self.title, str(self.mode), self.content,)
        p += "style=%s, span=%d, editable=%s)"    % (str(self.style), int(self.span), str(self.editable),)
        return p
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("title"):
            self.set_title(j["title"])
        if j.has_key("mode"):
            self.set_mode(j["mode"])
        if j.has_key("content"):
            self.set_content(j["content"])
        if j.has_key("style"):
            self.set_style(j["style"])
        if j.has_key("span"):
            self.set_span(j["span"])
        if j.has_key("editable"):
            self.set_editable(j["editable"])
        if j.has_key("id"):
            self.id = j["id"]

class PlotPanel(Panel):
    def __init__(self, targets=[], datasource="", title="", error=False,
                       editable=True, isNew=True, links=[], span=12):
        Panel.__init__(self, span=span, editable=editable, title=title)
        self.links = links
        self.isNew = isNew
        self.error = error
        self.datasource = datasource
        self.targets = targets
    def set_isNew(self, b):
        if isinstance(b, bool):
            self.isNew = b
    def set_error(self, b):
        if isinstance(b, bool):
            self.error = b  
    def set_datasource(self, d):
        if isinstance(d, str):
            self.datasource = d
    def set_title(self, t):
        self.title = str(t)
    def add_link(self, l):
        self.links.append(l)
    def add_target(self, t):
        if isinstance(t, Target):
            x = copy.deepcopy(t)
            self.targets.append(x)
    def get(self):
        return {"datasource" : self.datasource, "title" : self.title,
                "error" : self.error, "isNew" : self.isNew,
                "span" : self.span, "editable": self.editable,
                "id": self.id, "targets" : [t.get() for t in self.targets ]}
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        p = "PlotPanel(targets=%s, datasource=\"%s\", " % (str([t.__repr__() for t in self.targets ]), self.datasource, )
        p += "title=\"%s\", error=%s, " % (self.title, str(self.error), )
        p += "editable=%s, isNew=%s, " % (str(self.editable), str(self.isNew), )
        p += "links=%s, span=%d)"  % (str(self.links), int(span), )
        return p
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("datasource"):
            self.set_datasource(j["datasource"])
        if j.has_key("title"):
            self.set_title(j["title"])
        if j.has_key("error"):
            self.set_error(j["error"])
        if j.has_key("isNew"):
            self.set_isNew(j["isNew"])
        if j.has_key("links"):
            self.set_links(j["links"])
        if j.has_key("span"):
            self.set_span(j["span"])
        if j.has_key("editable"):
            self.set_editable(j["editable"])
        if j.has_key("id"):
            self.id = j["id"]
    

class SeriesOverride(object):
    def __init__(self, alias):
        self.alias = alias
        self.bars = None
        self.lines = None
        self.fill = None
        self.linewidth = None
        self.fillBelowTo = None
        self.steppedLine = None
        self.points = None
        self.pointradius = None
        self.stack = None
        self.yaxis = None
        self.zindex = None
    def get(self):
        d = {"alias" : self.alias}
        if self.bars and isinstance(self.bars, bool):
            d.update({"bars" : self.bars})
        if self.lines and isinstance(self.lines, bool):
            d.update({"lines" : self.lines})
        if self.fill and isinstance(self.fill, int) and self.fill in range(11):
            d.update({"fill" : self.fill})
        if self.linewidth and isinstance(self.linewidth, int) and self.linewidth in range(11):
            d.update({"linewidth" : self.linewidth})
        if self.fillBelowTo and isinstance(self.linewidth, str):
            d.update({"fillBelowTo" : self.fillBelowTo})
        if isinstance(self.steppedLine, bool):
            d.update({"steppedLine" : self.steppedLine})
        if isinstance(self.points, bool):
            d.update({"points" : self.points})
        if self.pointradius and isinstance(self.linewidth, int) and self.pointradius in range(1,6):
            d.update({"pointradius" : self.pointradius})
        if self.stack and self.stack in [True, False, 2, 3, 4, 5]:
            d.update({"stack" : self.stack})
        if self.yaxis and self.yaxis in [1, 2]:
            d.update({"yaxis" : self.yaxis})
        if self.zindex and isinstance(self.linewidth, int) and self.linewidth in range(-3,4):
            d.update({"zindex" : self.zindex})
        return d
    def set_bars(self, b):
        if isinstance(b, bool):
            self.bars = b
        else:
            self.bars = None
    def set_lines(self, b):
        if isinstance(b, bool):
            self.lines = b
        else:
            self.lines = None
    def set_steppedLine(self, b):
        if isinstance(b, bool):
            self.steppedLine = b
        else:
            self.steppedLine = None
    def set_points(self, b):
        if isinstance(b, bool):
            self.points = b
        else:
            self.points = None
    def set_stack(self, b):
        if isinstance(b, bool):
            self.stack = b
        elif isinstance(b, int) and b in range(2,6):
            self.stack = b
        else:
            self.stack = None
    def set_pointradius(self, b):
        if isinstance(b, int) and b in range(1,6):
            self.pointradius = b
        else:
            self.pointradius = None
    def set_yaxis(self, b):
        if isinstance(b, int) and b in [1, 2]:
            self.yaxis = b
        else:
            self.yaxis = None
    def set_zindex(self, b):
        if isinstance(b, int) and b in range(-3,4):
            self.zindex = b
        else:
            self.zindex = None
    def set_linewidth(self, b):
        if isinstance(b, int) and b in range(11):
            self.linewidth = b
        else:
            self.linewidth = None
    def set_fill(self, b):
        if isinstance(b, int) and b in range(11):
            self.fill = b
        else:
            self.fill = None
    def set_fillBelowTo(self, b):
        if isinstance(b, str):
            self.alias = b
            self.fillBelowTo = b
            self.lines = False
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())


class Graph(PlotPanel):
    def __init__(self, bars=False, timeFrom=None, links=[], isNew=True, nullPointMode="connected",
                       renderer="flot", linewidth=2, steppedLine=False, fill=0,
                       span=12, title="", tooltip=Tooltip(), targets=[],
                       seriesOverrides=[], percentage=False, xaxis=True,
                       error=False, editable=True, stack=False, yaxis=True,
                       timeShift=None, aliasColors={}, lines=True, points=False,
                       datasource="", pointradius=5, y_formats=[], legend=Legend(),
                       leftYAxisLabel=None, rightYAxisLabel=None, grid=Grid()):
        PlotPanel.__init__(self, title=title, isNew=isNew, targets=targets, links=links,
                         datasource=datasource, error=error, span=span, editable=editable)
        self.type = "graph"
        self.set_bars(bars)
        self.timeFrom = timeFrom
        self.nullPointMode = nullPointMode
        self.renderer = renderer
        self.linewidth = linewidth
        self.set_steppedLine(steppedLine)
        self.fill = fill
        self.seriesOverrides = seriesOverrides
        self.set_percentage(percentage)
        self.set_xaxis(xaxis)
        self.grid = grid
        self.tooltip = tooltip
        self.legend = legend
        self.set_stack(stack)
        self.set_yaxis(yaxis)
        self.timeShift = timeShift
        self.aliasColors = aliasColors
        self.set_lines(lines)
        self.set_points( points)
        self.set_pointradius(pointradius)
        self.validYFormats = ['bytes', 'bits', 'bps', 'Bps', 'short', 'joule', 'watt', 'ev', 'none']
        self.y_formats = y_formats
        self.leftYAxisLabel = leftYAxisLabel
        self.rightYAxisLabel = rightYAxisLabel
    def set_nullPointMode(self, m):
        if m in ["connected", 'null as zero']:
            self.nullPointMode = m
    def add_seriesOverride(self, b):
        if isinstance(b, SeriesOverride):
            self.seriesOverride.append(b)
    def set_bars(self, b):
        if isinstance(b, bool):
            self.bars = b
    def set_steppedLine(self, b):
        if isinstance(b, bool):
            self.steppedLine = b
    def set_percentage(self, b):
        if isinstance(b, bool):
            self.percentage = b
    def set_xaxis(self, b):
        if isinstance(b, bool):
            self.xaxis = b
    def set_yaxis(self, b):
        if isinstance(b, bool):
            self.yaxis = b
    def set_stack(self, b):
        if isinstance(b, bool):
            self.stack = b
    def set_lines(self, b):
        if isinstance(b, bool):
            self.lines = b
    def set_points(self, b):
        if isinstance(b, bool):
            self.points = b
    def set_linewidth(self, b):
        if isinstance(b, int):
            self.linewidth = b
    def set_fill(self, b):
        if isinstance(b, int):
            self.fill = b
    def set_y_formats(self, left, right):
        if left in self.validYFormats:
            self.y_formats[0] = left
        if right in self.validYFormats:
            self.y_formats[1] = right
    def set_pointradius(self, b):
        if isinstance(b, int):
            self.pointradius = b
        elif isinstance(b, str):
            try:
                self.pointradius = int(b)
            except:
                pass
    def set_leftYAxisLabel(self, l):
        self.leftYAxisLabel = str(l)
    def set_rightYAxisLabel(self, l):
        self.rightYAxisLabel = str(l)
    def get(self):
        yfmt = ["short","short"]
        if len(self.y_formats) > 0:
            yfmt = self.y_formats
        g = {"bars" : self.bars, "timeFrom" : self.timeFrom, "links" : self.links,
                "isNew" : self.isNew, "nullPointMode" : self.nullPointMode,
                "renderer" : self.renderer, "linewidth" : self.linewidth,
                "steppedLine" : self.steppedLine, "id" : self.id, "fill" : self.fill,
                "span" : self.span, "title" : self.title, "tooltip" : self.tooltip.get(),
                "targets" : [ t.get() for t in self.targets], "grid" : self.grid.get(),
                "seriesOverrides" : self.seriesOverrides, "percentage" : self.percentage,
                "type" : self.type, "x-axis" : self.xaxis, "error" : self.error,
                "editable" : self.editable, "legend" : self.legend.get(), "stack" : self.stack,
                "y-axis" : self.yaxis, "timeShift" : self.timeShift,
                "aliasColors" : self.aliasColors, "lines" : self.lines,
                "points" : self.points, "datasource" : self.datasource,
                "pointradius" : self.pointradius, "y_formats" : yfmt}
        if self.leftYAxisLabel:
            g.update({"leftYAxisLabel" : self.leftYAxisLabel})
        if self.rightYAxisLabel:
            g.update({"rightYAxisLabel" : self.rightYAxisLabel})
        return g
    
class Gauge(object):
    def __init__(self, maxValue=None, minValue=None, show=None, thresholdLabels=None, thresholdMarkers=None):
        self.maxValue = maxValue
        self.minValue = minValue
        self.show = show
        self.thresholdLabels = thresholdLabels
        self.thresholdMarkers = thresholdMarkers
        self.default_maxValue = 100
        self.default_minValue = 0
        self.default_show = False
        self.default_thresholdLabels = False
        self.default_thresholdMarkers = True
    def set_show(self, b):
        if isinstance(b, bool):
            self.show = b
            return True
        return False
    def set_thresholdLabels(self, b):
        if isinstance(b, bool):
            self.thresholdLabels = b
            return True
        return False
    def set_thresholdMarkers(self, b):
        if isinstance(b, bool):
            self.thresholdMarkers = b
            return True
        return False
    def set_maxValue(self, b):
        if not isinstance(b, int):
            try:
                b = int(b)
            except:
                print "maxValue must be an integer"
                return False
        self.maxValue = b
        return True
    def set_minValue(self, b):
        if not isinstance(b, int):
            try:
                b = int(b)
            except:
                print "minValue must be an integer"
                return False
        self.minValue = b
        return True
    def get(self):
        maV = self.maxValue
        if not maV:
            maV = self.default_maxValue
        miV = self.maxValue
        if not miV:
            miV = self.default_minValue
        s = self.show
        if not s:
            s = self.default_show
        tl = self.thresholdLabels
        if not tl:
            tl = self.default_thresholdLabels
        tm = self.thresholdMarkers
        if not tm:
            tm = self.default_thresholdMarkers
        return {"maxValue" : maV, "minValue" : miV,
                "show" : s, "thresholdLabels" : tl,
                "thresholdMarkers" : tm}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        if not isinstance(j, dict):
            j = json.loads(j)
        if j.has_key("maxValue"):
            self.set_maxValue(j["maxValue"])
        if j.has_key("minValue"):
            self.set_minValue(j["minValue"])
        if j.has_key("show"):
            self.set_show(j["show"])
        if j.has_key("thresholdLabels"):
            self.set_thresholdLabels(j["thresholdLabels"])
        if j.has_key("thresholdMarkers"):
            self.set_thresholdMarkers(j["thresholdMarkers"])

class Sparkline(object):
    def __init__(self, fillColor=None, full=None,
                       lineColor=None, show=None):
        self.fillColor = fillColor
        self.full = full
        self.lineColor = lineColor
        self.show = show
        self.default_fillColor = "rgba(31, 118, 189, 0.18)"
        self.default_lineColor = "rgb(31, 120, 193)"
        self.default_full = False
        self.default_show = False
    def set_full(self, b):
        if isinstance(b, bool):
            self.full = b
            return True
        return False
    def set_show(self, b):
        if isinstance(b, bool):
            self.show = b
            return True
        return False
    def set_fillColor(self, c):
        c = check_color(c)
        if c:
            self.fillColor = c
            return True
        return False
    def set_lineColor(self, c):
        c = check_color(c)
        if c:
            self.lineColor = c
            return True
        return False
    def get(self):
        fc = self.fillColor
        if not fc:
            fc = self.default_fillColor
        lc = self.lineColor
        if not lc:
            lc = self.default_lineColor
        f = self.full
        if not f:
            f = self.default_full
        s = self.show
        if not s:
            s = self.default_show
        return { "fillColor" : str(fc), "full" : f,
                 "lineColor" : str(fc), "show" : s }
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        if not isinstance(j, dict):
            j = json.loads(j)
        if j.has_key("fillColor"):
            self.set_fillColor(j["fillColor"])
        if j.has_key("lineColor"):
            self.set_lineColor(j["lineColor"])
        if j.has_key("full"):
            self.set_full(j["full"])
        if j.has_key("show"):
            self.set_show(j["show"])

class SingleStat(PlotPanel):
    def __init__(self, cacheTimeout=None, colorBackground=False, colorValue=False,
                       colors=[], datasource="", editable=True, error=False,
                       format="none", gauge=Gauge(), interval=None,
                       isNew=True, links=[], maxDataPoints=100,
                       NonePointMode="connected", NoneText=None, postfix="",
                       postfixFontSize="50%", prefix="", prefixFontSize="50%",
                       span=3, sparkline=Sparkline(), targets=[], thresholds="",
                       title="", valueFontSize="80%", valueMaps=[], valueName="avg"):

        PlotPanel.__init__(self, title=title, isNew=isNew, targets=targets, links=links,
                         datasource=datasource, error=error, span=span, editable=editable)
        self.type = "singlestat"
        self.cacheTimeout = cacheTimeout
        self.colorBackground = colorBackground
        self.colorValue = colorValue
        self.colors = colors
        self.format = format
        self.gauge = gauge
        self.interval = interval
        self.maxDataPoints = maxDataPoints
        self.NonePointMode = NonePointMode
        self.NoneText = NoneText
        self.validFontSizes = ['20%', '30%','50%','70%','80%','100%', '110%', '120%', '150%', '170%', '200%']
        self.postfix = postfix
        #self.postfixFontSize = postfixFontSize
        self.set_postFontSize(postfixFontSize)
        self.prefix = prefix
        self.set_prefixFontSize(prefixFontSize)
        #self.prefixFontSize = prefixFontSize
        self.sparkline = sparkline
        self.thresholds = thresholds
        self.valueFontSize = valueFontSize
        self.valueMaps = valueMaps
        self.validValueNames = ['min','max','avg', 'current', 'total', 'name']
        self.set_valueName(valueName)
    def set_colorBackground(self, b):
        if isinstance(b, bool):
            self.colorBackground = b
    def set_colorValue(self, b):
        if isinstance(b, bool):
            self.colorValue = b
    def set_editable(self, b):
        if isinstance(b, bool):
            self.editable = b
    def set_error(self, b):
        if isinstance(b, bool):
            self.error = b
    def set_isNew(self, b):
        if isinstance(b, bool):
            self.isNew = b
    def set_valueName(self, v):
        if v in self.validValueNames:
            self.valueName = v
        else:
            print "invalid value %s for valueName" % (v,)
    def set_prefixFontSize(self, v):
        if v in self.validFontSizes:
            self.prefixFontSize = v
        else:
            print "invalid value %s for prefixFontSize" % (v,)
    def set_postFontSize(self, v):
        if v in self.validFontSizes:
            self.postfixFontSize = v
        else:
            print "invalid value %s for postfixFontSize" % (v,)
    def set_valueFontSize(self, v):
        if v in self.validFontSizes:
            self.valueFontSize = v
        else:
            print "invalid value %s for valueFontSize" % (v,)
    def add_valueMap(self, value, text, operator="="):
        self.valueMaps.append({ "value" : value, "op" : operator, "text": text })
    def add_rangeMap(self, start, end, text ):
        self.valueMaps.append({ "from": start, "to": end, "text": text })
    def add_color(self, c):
        if check_color(c):
            self.colors.append(c)
    def invert_colors(self):
        self.colors = self.colors[::-1]
    def get(self):
        vmaps = []
        if len(self.valueMaps) == 0:
            vmaps.append( { "op" : "=", "text" : "N/A", "value" : "None" })
        c = ["rgba(245, 54, 54, 0.9)", "rgba(237, 129, 40, 0.89)", "rgba(50, 172, 45, 0.97)"]
        if len(self.colors) > 0:
            c = self.colors
        return { "cacheTimeout": self.cacheTimeout, "colorBackground": self.colorBackground,
                 "colorValue": self.colorValue, "colors": c,
                 "datasource": self.datasource, "editable": self.editable,
                 "error": self.error, "format": self.format, "gauge": self.gauge.get(),
                 "id": self.id, "interval": self.interval, "isNew": self.isNew,
                 "links": self.links, "maxDataPoints": self.maxDataPoints,
                 "NonePointMode": self.NonePointMode, "NoneText": self.NoneText,
                 "postfix": self.postfix, "postfixFontSize": self.postfixFontSize,
                 "prefix": self.prefix, "prefixFontSize": self.prefixFontSize,
                 "span": self.span, "sparkline": self.sparkline.get(),
                 "targets": [ t.get() for t in self.targets], "thresholds": self.thresholds,
                 "title": self.title, "type": self.type,
                 "valueFontSize": self.valueFontSize, "valueName": self.valueName,
                 "valueMaps": vmaps }

class Row(object):
    def __init__(self, title="", panels=[], editable=False, collapse=False, height="250px"):
        self.title = title
        self.panels = panels
        self.editable = editable
        self.collapse = collapse
        self.height = height
    def set_title(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Title must be stringifyable"
                return False
        self.title = t
        return True
    def set_height(self, h):
        if not isinstance(h, str):
            try:
                h = str(h)
            except ValueError:
                print "Height must be stringifyable"
                return False
        self.height = h
        return True
    def set_editable(self, b):
        if isinstance(b, bool):
            self.editable = b
            return True
        return False
    def set_collapse(self, b):
        if isinstance(b, bool):
            self.collapse = b
            return True
        return False
    def add_panel(self, p):
        if isinstance(p, Panel):
            x = copy.deepcopy(p)
            self.panel.append(x)
            return True
        return False
    def get(self):
        return {'title': self.title, 'panels': [ p.get() for p in self.panels ],
                'editable': self.editable, 'collapse': self.collapse,
                'height': self.height}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def add_panel(self, p):
        if isinstance(p, Panel):
            x = copy.deepcopy(p)
            self.panels.append(x)
    def set_datasource(self, d):
        for p in self.panels:
            p.set_datasource(d)
    def set_height(self, h):
        if re.match("\d+px"):
            self.height = h
    def read_json(self, j):
        if not isinstance(j, dict):
            j = json.loads(j)
        if j.has_key("title"):
            self.set_title(j["title"])
        if j.has_key("editable"):
            self.set_editable(j["editable"])
        if j.has_key("collapse"):
            self.set_collapse(j["collapse"])
        if j.has_key("height"):
            self.set_height(j["height"])
        if j.has_key("panels"):
            for p in j["panels"]:
                o = None
                if p.has_key("type"):
                    if p["type"] == "singlestat":
                        o = SingleStat()
                        o.read_json(p)
                    if p["type"] == "graph":
                        o = Graph()
                        o.read_json(p)
                    if p["type"] == "text":
                        o = TextPanel()
                        o.read_json(p)
                if o:
                    self.add_panel(o)
                    return True
                return False


class Template(object):
    def __init__(self, name, value, multi=True, allFormat="regex wildcard",
                       refresh=True, options=[], current={}, datasource="", tags=[],
                       type="query", multiFormat="regex values", includeAll=False):
        self.multi = multi
        self.name = name
        self.value = value
        self.allFormat = allFormat
        self.refresh = refresh
        self.options = options
        self.current = current
        self.datasource = datasource
        self.tags = tags
        self.type = type
        self.multiFormat = multiFormat
        self.includeAll = includeAll
        self.validAllFormats = ["regex wildcard"]
        self.validMultiFormats = ["regex values"]
        self.validTypes = ["query", "interval", "custom"]
    def _set_name_and_value(self, n, v):
        if not isinstance(n, str):
            try:
                n = str(n)
            except:
                print "Name but by stringifyable"
                return False
        if not isinstance(v, str):
            try:
                v = str(v)
            except:
                print "Value but by stringifyable"
                return False
        self.name = n
        self.value = v
        return True
    def set_datasource(self, d):
        self.datasource = d
    def set_multi(self, b):
        if isinstance(b, bool):
            self.multi = b
    def set_refresh(self, b):
        if isinstance(b, bool):
            self.refresh = b
    def set_includeAll(self, b):
        if isinstance(b, bool):
            self.includeAll = b
    def set_type(self, t):
        if t in self.validTypes:
            self.type = t
    def set_allFormat(self, s):
        if s in self.validAllFormats:
            self.allFormat = s
    def set_multiFormat(self, s):
        if s in self.validMultiFormats:
            self.multiFormat = s
    def add_option(self, t):
        if isinstance(t, list):
            self.options = copy.deepcopy(t)
            return True
        elif isinstance(t, str):
            self.options.append(t)
            return True
        return False
    def add_tag(self, t):
        if isinstance(t, list):
            self.tags = copy.deepcopy(t)
            return True
        elif isinstance(t, str):
            self.tags.append(t)
            return True
        return False
    def get(self):
        q = self.value
        if self.type == "query" and self.datasource == "influxdb":
            q = "SHOW TAG VALUES WITH KEY = %s" % (self.value,)
            if len(self.tags) > 0:
                l = []
                for i, t in enumerate(self.tags):
                    k,v = t
                    v = v.strip("/")
                    if v[0] == "$" and v[-1] != "$":
                        v += "$"
                    l.append("%s =~ /%s/" % (k, v))
                q += " WHERE "+" AND ".join(l)
        return {"multi" : self.multi, "name" : self.name, "allFormat" : self.allFormat,
                "refresh" : self.refresh, "options" : self.options,
                "current" : self.current, "datasource" : self.datasource,
                "query": q, "type" : self.type,
                "multiFormat" : self.multiFormat, "includeAll" : self.includeAll}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        if not isinstance(j, dict):
            j = json.loads(j)
        if j.has_key('name') and j.has_key('value'):
            self._set_name_and_value(j['name'], j['value'])
        if j.has_key('name') and j.has_key('query'):
            self._set_name_and_value(j['name'], j['query'])
        if j.has_key('allFormat'):
            self.set_allFormat(j['allFormat'])
        if j.has_key('type'):
            self.set_type(j['type'])
        if j.has_key('datasource'):
            self.set_datasource(j['datasource'])
        if j.has_key('refresh'):
            self.set_refresh(j['refresh'])
        if j.has_key('multiFormat'):
            self.set_refresh(j['multiFormat'])
        if j.has_key('includeAll'):
            self._set_includeAll(j['includeAll'])
        if j.has_key('multi'):
            self._set_multi(j['multi'])

class Timepicker(object):
    def __init__(self, time_options=['5m', '15m', '1h', '6h', '12h', '24h', '2d', '7d', '30d'],
                       refresh_intervals=['5s', '10s', '30s', '1m', '5m', '15m', '30m', '1h', '2h', '1d']):
        self.time_options = time_options
        self.refresh_intervals = refresh_intervals
    def set_time_options(self, t):
        if isinstance(t, list):
            self.time_options = copy.deepcopy(t)
            return True
        elif isinstance(t, str):
            self.time_options.append(t)
            return True
        return False
    def set_refresh_intervals(self, t):
        if isinstance(t, list):
            self.refresh_intervals = copy.deepcopy(t)
            return True
        elif isinstance(t, str):
            self.refresh_intervals.append(t)
            return True
        return False
    def get(self):
        return {'time_options': self.time_options,
                'refresh_intervals': self.refresh_intervals}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def read_json(self, j):
        if not isinstance(j, dict):
            j = json.loads(j)
        if j.has_key('time_options') and isinstance(j['time_options'], list):
            self.set_time_options(j['time_options'])
        if j.has_key('refresh_intervals') and isinstance(j['refresh_intervals'], list):
            self.set_refresh_intervals(j['refresh_intervals'])

dashboard_id = 0

class Dashboard(object):
    def __init__(self, title, style='dark', rows=[], links=[], tags=[], hideControls=False,
                       editable=True, originalTitle="", timepicker=Timepicker(),
                       refresh='10s', sharedCrosshair=False, timezone='browser',
                       schemaVersion=8, overwrite=False, templates=[], annotations=[],
                       startTime="now-6h", endTime="now"):
        global dashboard_id
        self.id = dashboard_id
        dashboard_id += 1
        self.templates = templates
        self.rows = rows
        self.style = style
        self.links = links
        self.tags = tags
        self.hideControls = hideControls
        self.title = title
        self.editable = editable
        self.originalTitle = originalTitle
        self.timepicker = timepicker
        self.refresh = refresh
        self.sharedCrosshair = sharedCrosshair
        self.timezone = timezone
        self.schemaVersion = schemaVersion
        self.annotations = annotations
        self.overwrite = overwrite
        self.startTime = startTime
        self.endTime = endTime
        self.validStyles = ["light", "dark"]
    def add_template(self, t):
        if isinstance(t, Template):
            x = copy.deepcopy(t)
            self.templates.append(x)
            return True
        return False
    def add_row(self, r):
        if isinstance(r, Row):
            x = copy.deepcopy(r)
            self.rows.append(x)
            return True
        return False
    def add_tag(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Tag must be stringifyable"
                return False
        self.tag.append(t)
        return True
    def set_timepicker(self, t):
        if isinstance(t, Timepicker):
            x = copy.deepcopy(t)
            self.timepicker = x
            return True
        elif isinstance(t, dict):
        
            x = Timepicker()
    def set_overwrite(self, b):
        if isinstance(b, bool):
            self.overwrite = b
            return True
        return False
    def set_editable(self, b):
        if isinstance(b, bool):
            self.editable = b
            return True
        return False
    def set_hideControls(self, b):
        if isinstance(b, bool):
            self.hideControls = b
            return True
        return False
    def set_sharedCrosshair(self, b):
        if isinstance(b, bool):
            self.sharedCrosshair = b
            return True
        return False
    def set_title(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Title must be stringifyable"
                return False
        self.title = t
        return True
    def set_originalTitle(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Title must be stringifyable"
                return False
        self.originalTitle = t
        return True
    def set_refresh(self, r):
        if isinstance(r, str) and r[-1] in time_limits.keys():
            self.refresh = r
            return True
        return False
    def set_version(self, v):
        if not isinstance(v, int):
            try:
                v = int(v)
            except ValueError:
                print "Input parameter %s must be castable to integer" % (v,)
                return False
        self.version = v
        return True
    def set_timezone(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Timezone must be stringifyable"
                return False
        self.timezone = t
        return True
    def set_style(self, s):
        if s in self.validStyles:
            self.style = s
    def set_startTime(self, t):
        # check time
        if isinstance(t, str):
            self.startTime = t
        if isinstance(t, int) or isinstance(t, float) or isinstance(t, datetime.datetime):
            self.startTime = str(t)
    def set_endTime(self, t):
        # check time
        if isinstance(t, str):
            self.endTime = t
        if isinstance(t, int) or isinstance(t, float) or isinstance(t, datetime.datetime):
            self.endTime = str(t)
    def get(self):
        origTitle = self.originalTitle
        if not origTitle:
            origTitle = self.title
        return {'dashboard': {'version': 0, 'style': self.style, 'rows': [ r.get() for r in self.rows ],
                'templating': {'list': [ t.get() for t in self.templates] }, 'links': self.links,
                'tags': self.tags, 'hideControls': self.hideControls,
                'title': self.title, 'editable': self.editable, 'id': self.id,
                'originalTitle': origTitle, 'timepicker': self.timepicker.get(),
                'refresh': self.refresh, 'sharedCrosshair': self.sharedCrosshair,
                'time': {'to': self.endTime, 'from': self.startTime}, 'timezone': self.timezone,
                'schemaVersion': 8, 'annotations': {'list': self.annotations}},
                'overwrite': self.overwrite}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def set_datasource(self, d):
        for r in self.rows:
            r.set_datasource(d)
        for t in self.templates:
            t.set_datasource(d)


def read_json(self, dstr="{}"):
    dash = None
    try:
        dash = json.loads(dstr)
    except ValueError as e:
        print e
        return None
    if isinstance(dash, dict):
        if dash.has_key("dashboard"):
            out = read_json(str(dash["dashboard"]))
            if isinstance(out, Dashboard):
                out.set_overwrite(dash["overwrite"])
            return out
        elif dash.has_key("title"):
            out = Dashboard(dash["title"])
            if dash.has_key("version"):
                out.set_version(dash["version"])
            if dash.has_key("links"):
                out.set_style(dash["links"])
            if dash.has_key("tags"):
                out.set_version(dash["tags"])
            if dash.has_key("hideControls"):
                out.set_hideControls(dash["hideControls"])
            if dash.has_key("editable"):
                out.set_editable(dash["editable"])
            if dash.has_key("originalTitle"):
                out.set_originalTitle(dash["originalTitle"])
            if dash.has_key("refresh"):
                out.set_refresh(dash["refresh"])
            if dash.has_key("sharedCrosshair"):
                out.set_sharedCrosshair(dash["sharedCrosshair"])
            if dash.has_key("timezone"):
                out.set_timezone(dash["timezone"])
            if dash.has_key("time"):
                if dash["time"].has_key("from"):
                    out.set_startTime(dash["time"]["from"])
                if dash["time"].has_key("to"):
                    out.set_endTime(dash["time"]["to"])
            if dash.has_key("timepicker"):
                t = Timepicker(refresh_intervals=[], time_options=[])
                if dash["timepicker"].has_key("refresh_intervals"):
                    t.set_refresh_intervals(dash["timepicker"]["refresh_intervals"])
                if dash["timepicker"].has_key("time_options"):
                    t.set_time_options(dash["timepicker"]["time_options"])
                out.set_timepicker(t)
            if dash.has_key("rows"):
                for row in data["rows"]:
                    r = Row()
                    r.read_json(row)
            return dash
        else:
            print "Not a Grafana dashboard"
            return None
    else:
        return None

if __name__ == "__main__":
    t = Target("cpi")
    t.set_alias("CPI")
    t.add_tag("host","$hostname", operator="=~")
    t.add_groupBy("tag", "host")
    t.set_refId(1)
    g = Graph()
    g.add_target(t)
    b = SingleStat()
    b.add_target(t)
    c = SingleStat()
    r = Row()
    print r.get_json()
    r.add_panel(b)
    r.add_panel(c)
    print r.get_json()
    te = Template("hostname", "host", tags=[("jobid", "1234.tbadm")])
    d = Dashboard("Test")
    d.add_row(r)
    d.add_template(te)
    d.set_datasource("fepa")
    d.set_refresh("10s")
    print d
    
    sO = SeriesOverride("cpi")
    sO.set_bars(True)
    sO.set_points(False)
    print sO
