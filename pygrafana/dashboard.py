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
        self.validLogBases = [1, 2, 10, 32, 1024]
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

panel_id = 1



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
            return True
        return False
    def set_title(self, title):
        if isinstance(title, str):
            self.title = title
            return True
        return False
    def set_span(self, span):
        if isinstance(span, int) and span in range(1,13):
            self.span = span
            return True
        return False
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
                       style={}, span=12, editable=True, error=False,
                       links=[], transparent=False, repeat=None, minSpan=None):
        Panel.__init__(self, span=span, editable=editable, title=title)
        self.set_mode(mode)
        self.set_content(content)
        self.style = style
        self.set_error(error)
        self.set_repeat(repeat)
        if isinstance(links, list):
            self.links = []
            for l in links:
                if l["type"] == "absolute":
                    self.add_link(title=l["title"], typ="absolute", url=l["url"])
                elif l["type"] == "dashboard":
                    self.add_link(title=l["title"], typ="dashboard", dashboard=l["dashboard"])
                
        self.set_transparent(transparent)
        self.set_minSpan(minSpan)
        self.type = 'text'
    def set_mode(self, m):
        if m in ['html', 'markdown', 'text']:
            self.mode = m
            return True
        return False
    def set_title(self, title):
        if isinstance(title, str):
            self.title = title
            return True
        return False
    def set_content(self, content):
        if isinstance(content, str):
            self.content = content
            return True
        return False
    def set_error(self, error):
        if isinstance(error, bool):
            self.error = error
            return True
        return False
    def set_transparent(self, transparent):
        if isinstance(transparent, bool):
            self.transparent = transparent
            return True
        return False
    def set_minSpan(self, minSpan):
        if minSpan == None or isinstance(minSpan, int):
            self.minSpan = minSpan
            return True
        return False
    def set_repeat(self, repeat):
        if repeat == None or isinstance(repeat, str):
            self.repeat = repeat
            return True
        return False
    def set_style(self, style):
        if isinstance(style, dict):
            self.style = style
            return True
        return False
    def add_link(self, title="", typ="dashboard", url=None, dashboard=None):
        if typ not in ["absolute", "dashboard"]:
            print "Invalid link type"
            return False
        if typ == "absolute" and not url:
            print "For type 'absolute' an url is required"
            return False
        elif typ == "absolute":
            self.links.append({
              "type": typ,
              "url": url,
              "title": title,
              
            })
        if typ == "dashboard" and not dashboard:
            print "For type 'dashboard' a dashboard name is required"
            return False
        elif typ == "dashboard":
            self.links.append({
              "type": typ,
              "dashboard": dashboard,
              "title": title,
              "dashUri" : "db/"+dashboard.lower().replace("_","-")
            })
        return True
    def get(self):
        return {"title" : self.title, "mode" : self.mode,
                "content" : self.content, "style" : self.style,
                "span" : self.span, "editable": self.editable,
                "id": self.id, "type" : self.type,"error": self.error,
                "links" : self.links, "transparent" : self.transparent,
                "repeat" : self.repeat, "minSpan" : self.minSpan}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        links = ""
        for l in self.links:
            if l["type"] == "absolute":
                links += "{\"type\" : \"absolute\", \"title\" : \"%s\", \"url\" : \"%s\"}" % (l["title"], l["url"],)
            elif l["type"] == "dashboard":
                links += "{\"type\" : \"dashboard\", \"title\" : \"%s\", \"dashboard\" : \"%s\"}" % (l["title"], l["dashboard"],)
        p = "Textpanel(title=\"%s\", mode=\"%s\", content=\"%s\", " % (self.title, str(self.mode), self.content,)
        p += "style=%s, span=%d, editable=%s, " % (str(self.style), int(self.span), str(self.editable),)
        p += "links=[%s], transparent=%s, " % (links, str(self.transparent), )
        if self.repeat:
            p += "repeat=\"%s\", " % str(self.repeat)
        else:
            p += "repeat=None, "
        p += "minSpan=%s)" % str(self.minSpan)
        return p
    def read_json(self, j):
        if isinstance(j, str):
            j = json.loads(j)
        if j.has_key("type"):
            if j["type"] != 'text':
                print "No TextPanel"
                return False
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
        if j.has_key("transparent"):
            self.set_transparent(j["transparent"])
        if j.has_key("repeat"):
            self.set_repeat(j["repeat"])
        if j.has_key("minSpan"):
            self.set_repeat(j["minSpan"])
        if j.has_key("links"):
            for l in j["links"]:
                if l["type"] == "absolute":
                    self.add_link(title=l["title"], typ="absolute", url=l["url"])
                elif l["type"] == "dashboard":
                    self.add_link(title=l["title"], typ="dashboard", dashboard=l["dashboard"])
        if j.has_key("id"):
            self.id = j["id"]
        return True

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


class GraphPanel(PlotPanel):
    def __init__(self, bars=False, links=[], isNew=True, nullPointMode="connected",
                       renderer="flot", linewidth=2, steppedLine=False, fill=0,
                       span=12, title="", tooltip=Tooltip(), targets=[],
                       seriesOverrides=[], percentage=False, xaxis=True,
                       error=False, editable=True, stack=False, yaxis=True,
                       timeShift=None, aliasColors={}, lines=True, points=False,
                       datasource="", pointradius=5, y_formats=[], legend=Legend(),
                       leftYAxisLabel=None, rightYAxisLabel=None, grid=Grid(),
                       transparent=False, hideTimeOverride=False, timeFrom=None):
        self.validYFormats = ['bytes', 'kbytes', 'mbytes', 'gbytes', 'bits',
                              'bps', 'Bps', 'short', 'joule', 'watt', 'kwatt',
                              'watth', 'ev', 'amp', 'volt'
                              'none', 'percent', 'ppm', 'dB', 'ns', 'us',
                              'ms', 's', 'hertz', 'pps',
                              'celsius', 'farenheit', 'humidity',
                              'pressurembar', 'pressurehpa',
                              'velocityms', 'velocitykmh', 'velocitymph', 'velocityknot']
        self.validNullPointMode = ["connected", 'null as zero', 'null']
        self.validRenderer = ["png", "flot"]
        PlotPanel.__init__(self, title=title, isNew=isNew, targets=targets, links=links,
                         datasource=datasource, error=error, span=span, editable=editable)
        self.type = "graph"
        self.set_bars(bars)
        self.set_nullPointMode(nullPointMode)
        self.set_renderer(renderer)
        self.set_linewidth(linewidth)
        self.set_steppedLine(steppedLine)
        self.set_fill(fill)
        self.seriesOverrides = seriesOverrides
        self.set_percentage(percentage)
        self.set_xaxis(xaxis)
        self.grid = grid
        self.tooltip = tooltip
        self.legend = legend
        self.set_stack(stack)
        self.set_yaxis(yaxis)
        self.aliasColors = aliasColors
        self.set_lines(lines)
        self.set_points( points)
        self.set_pointradius(pointradius)
        self.set_hideTimeOverride(hideTimeOverride)
        self.set_transparent(transparent)
        self.set_timeShift(timeShift)
        self.set_timeFrom(timeFrom)
        
        left = 'short'
        right = 'short'
        if len(y_formats) > 0:
            left = y_formats[0]
        if len(y_formats) > 1:
            right = y_formats[1]
        self.set_y_formats(left, right)
        self.leftYAxisLabel = leftYAxisLabel
        self.rightYAxisLabel = rightYAxisLabel
    def set_nullPointMode(self, m):
        if m in self.validNullPointMode:
            self.nullPointMode = m
            return True
        return False
    def add_seriesOverride(self, b):
        if isinstance(b, SeriesOverride):
            self.seriesOverride.append(b)
            return True
        return False
    def set_bars(self, bars):
        if isinstance(bars, bool):
            self.bars = bars
            return True
        return False
    def set_timeFrom(self, timeFrom):
        if timeFrom == None or (isinstance(timeFrom, str) and timeFrom[-1] in time_limits.keys()):
            self.timeFrom = timeFrom
            return True
        return False
    def set_timeShift(self, timeShift):
        if timeShift == None or (isinstance(timeShift, str) and timeShift[-1] in time_limits.keys()):
            self.timeShift = timeShift
            return True
        return False
    def set_hideTimeOverride(self, hideTimeOverride):
        if isinstance(hideTimeOverride, bool):
            self.hideTimeOverride = hideTimeOverride
            return True
        return False
    def set_steppedLine(self, b):
        if isinstance(b, bool):
            self.steppedLine = b
            return True
        return False
    def set_transparent(self, transparent):
        if isinstance(transparent, bool):
            self.transparent = transparent
            return True
        return False
    def set_percentage(self, b):
        if isinstance(b, bool):
            self.percentage = b
            return True
        return False
    def set_xaxis(self, b):
        if isinstance(b, bool):
            self.xaxis = b
            return True
        return False
    def set_yaxis(self, b):
        if isinstance(b, bool):
            self.yaxis = b
            return True
        return False
    def set_stack(self, b):
        if isinstance(b, bool):
            self.stack = b
            return True
        return False
    def set_lines(self, b):
        if isinstance(b, bool):
            self.lines = b
            return True
        return False
    def set_points(self, b):
        if isinstance(b, bool):
            self.points = b
            return True
        return False
    def set_linewidth(self, b):
        if isinstance(b, int):
            self.linewidth = b
            return True
        return False
    def set_fill(self, b):
        if isinstance(b, int):
            self.fill = b
            return True
        return False
    def set_renderer(self, renderer):
        if isinstance(renderer, str) and renderer in self.validRenderer:
            self.renderer = renderer
            return True
        return False
    def set_y_formats(self, left, right):
        retl = False
        retr = False
        if not self.y_formats:
            self.y_formats= ('short', 'short')
        if left in self.validYFormats:
            self.y_formats[0] = left
            retl = True
        if right in self.validYFormats:
            self.y_formats[1] = right
            retr = True
        return ret
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
                "pointradius" : self.pointradius, "y_formats" : yfmt,
                "transparent" : self.transparent}
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

# TODO Check for dashboard validity:
#   - Repeat string for Row and Panels must be valid template name
#   - Template: add 'useTags' and others only if type == 'query'
#   - Warn if repeat template has multi == False

class Row(object):
    def __init__(self, title="", panels=[], editable=True, collapse=False, height="250px", showTitle=False, repeat=None):
        self.set_title(title)
        self.panels = []
        for p in panels:
            self.add_panel(p)
        self.set_editable(editable)
        self.set_collapse(collapse)
        self.set_height(height)
        self.set_showTitle(showTitle)
        self.set_repeat(repeat)
    def set_title(self, t):
        if not isinstance(t, str):
            try:
                t = str(t)
            except ValueError:
                print "Title must be stringifyable"
                return False
        self.title = t
        return True
    def set_height(self, height):
        if not isinstance(height, str):
            try:
                height = str(height)
            except ValueError:
                print "Height must be stringifyable"
                return False
        if not re.match("\d+px", height) and not re.match("\d+[cm]*", height):
            print "Height not valid"
            return False
        self.height = height
        return True
    def set_repeat(self, repeat):
        if repeat == None or isinstance(repeat, str):
            self.repeat = repeat
            return True
        return False
    def set_editable(self, editable):
        if isinstance(editable, bool):
            self.editable = editable
            return True
        return False
    def set_collapse(self, collapse):
        if isinstance(collapse, bool):
            self.collapse = collapse
            return True
        return False
    def set_showTitle(self, showTitle):
        if isinstance(showTitle, bool):
            self.showTitle = showTitle
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
                'height': self.height, 'repeat' : self.repeat}
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
                       type="query", multiFormat="regex values", includeAll=False,
                       label=None, hideLabel=False, auto_count=None, auto=False,
                       useTags=False, tagsQuery="", tagValuesQuery=""):
        self.validAllFormats = ["regex wildcard", "glob"]
        self.validMultiFormats = ["regex values", "glob"]
        self.validTypes = ["query", "interval", "custom"]
        self.validAutoCounts = [3, 5, 10, 30, 50, 100, 200]
        self._set_name_and_value(name, value)
        self.set_multi(multi)
        self.set_allFormat(allFormat)
        self.set_refresh(refresh)
        self.options = []
        for o in options:
            self.add_option(o)
        self.current = current
        self.set_datasource(datasource)
        self.tags = []
        for t in tags:
            self.add_tag(t)
        self.set_type(type)
        self.set_multiFormat(multiFormat)
        self.set_includeAll(includeAll)
        self.set_label(label)
        self.set_hideLabel(hideLabel)
        self.set_auto(auto)
        self.set_autoCount(auto_count)
        self.set_useTags(useTags)
        self.set_tagsQuery(tagsQuery)
        self.set_tagValuesQuery(tagValuesQuery)
    def _set_name_and_value(self, name, value):
        if not isinstance(name, str):
            try:
                name = str(name)
            except:
                print "Name not stringifyable"
                return False
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                print "Value not stringifyable"
                return False
        self.name = name
        self.value = value
        return True
    def set_useTags(self, useTags):
        if isinstance(useTags, bool):
            self.useTags = useTags
            return True
        return False
    def set_tagsQuery(self, tagsQuery):
        if isinstance(tagsQuery, str):
            self.tagsQuery = tagsQuery
            return True
        return False
    def set_tagValuesQuery(self, tagValuesQuery):
        if isinstance(tagValuesQuery, str):
            self.tagValuesQuery = tagValuesQuery
            return True
        return False
    def set_label(self, label):
        if label == None or isinstance(label, str):
            self.label = label
            return True
        return False
    def set_datasource(self, datasource):
        if isinstance(datasource, str):
            self.datasource = datasource
            return True
        return False
    def set_multi(self, multi):
        if isinstance(multi, bool):
            self.multi = multi
            return True
        return False
    def set_auto(self, auto):
        if isinstance(auto, bool):
            self.auto = auto
            return True
        return False
    def set_autoCount(self, autoCount):
        if autoCount == None or (isinstance(autoCount, int) and autoCount in self.validAutoCounts):
            self.auto_count = autoCount
            return True
        return False
    def set_hideLabel(self, hideLabel):
        if isinstance(hideLabel, bool):
            self.hideLabel = hideLabel
            return True
        return False
    def set_refresh(self, refresh):
        if isinstance(refresh, bool):
            self.refresh = refresh
            return True
        return False
    def set_includeAll(self, includeAll):
        if isinstance(includeAll, bool):
            self.includeAll = includeAll
            return True
        return False
    def set_type(self, typ):
        if typ in self.validTypes:
            self.type = typ
            return True
        return False
    def set_allFormat(self, allFormat):
        if allFormat in self.validAllFormats:
            self.allFormat = allFormat
            return True
        return False
    def set_multiFormat(self, multiFormat):
        if multiFormat in self.validMultiFormats:
            self.multiFormat = multiFormat
            return True
        return False
    def add_option(self, option):
        if isinstance(option, list):
            self.options = copy.deepcopy(option)
            return True
        elif isinstance(option, str):
            self.options.append(option)
            return True
        return False
    def add_tag(self, tag):
        if isinstance(tag, list):
            self.tags = copy.deepcopy(tag)
            return True
        elif isinstance(tag, str):
            self.tags.append(tag)
            return True
        return False
    def get(self):
        q = self.value
        if self.type == "query" and self.datasource == "influxdb" and not q.startswith("SHOW TAG VALUES WITH KEY"):
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
        elif self.type == "interval" or self.type == "custom":
            q = str(self.value)
        c = self.current
        if len(c) == 0 and len(self.value.split(",")) > 0:
            s = self.value.split(",")[0]
            c = {"text" : str(s), "value" : str(s)}
        d = {"multi" : self.multi, "name" : self.name, "allFormat" : self.allFormat,
                "refresh" : self.refresh, "options" : self.options,
                "current" : c, "datasource" : self.datasource,
                "query": q, "type" : self.type,
                "multiFormat" : self.multiFormat, "includeAll" : self.includeAll,
                "refresh_on_load" : self.refresh, "hideLabel" : self.hideLabel,
                "label" : self.label, "auto" : self.auto, "auto_count" : self.auto_count}#, ,
        if self.type == "query" and self.useTags == True:
            d.update({"useTags" : self.useTags,
                      "tagsQuery" : self.tagsQuery,
                      "tagValuesQuery" : self.tagValuesQuery})
        return d
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
            self.set_multiFormat(j['multiFormat'])
        if j.has_key('includeAll'):
            self.set_includeAll(j['includeAll'])
        if j.has_key('multi'):
            self.set_multi(j['multi'])
        if j.has_key('label'):
            self.set_label(j['label'])
        if j.has_key('hideLabel'):
            self.set_hideLabel(j['hideLabel'])
        if j.has_key('auto'):
            self.set_auto(j['auto'])
        if j.has_key('auto_count'):
            self.set_autoCount(j['auto_count'])
        if j.has_key('useTags'):
            self.set_useTags(j['useTags'])
        if j.has_key('tagsQuery'):
            self.set_tagsQuery(j['tagsQuery'])
        if j.has_key('tagValuesQuery'):
            self.set_tagValuesQuery(j['tagValuesQuery'])
        if j.has_key('query'):
            self.query(j['query'])


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
