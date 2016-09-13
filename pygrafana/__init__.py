#!/usr/bin/python

import copy
import json
import re

# s (seconds), m (minutes), h (hours), d (days), w (weeks), M (months), y (years
time_limits = { "s" : 60, "m" : 60, "h" : 24, "d" : 31, "w": 52, "M" : 12, "y" : 100}
def check_timerange(t):
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
    m = re.match("rgba\((\d+),\s*(\d+),\s*(\d+),\s*(0.[\d]+)\)", c)
    if m and int(m.group(1)) < 255 and int(m.group(2)) < 255 and int(m.group(3)) < 255 and float(m.group(4)) > 0 and float(m.group(4)) <= 1:
        return c
    m = re.match("rgb\((\d+),\s*(\d+),\s*(\d+)\)", c)
    if m and int(m.group(1)) < 255 and int(m.group(2)) < 255 and int(m.group(3)) < 255:
        return c
    m = re.match("#[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]$", c)
    if m:
        return c
    return None

target_id = 0

class Target(object):
    def __init__(self, measurement, dsType="influxdb", alias="", tags=[],
                  groupBy=[], select=[], query="", resultFormat="time_series"):
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
    def get(self):
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
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())
    def set_dsType(self, dsType):
        self.dsType = str(dsType)
    def set_refId(self, refId):
        self.refId = refId
    def set_alias(self, alias):
        self.alias = str(alias)
    def set_resultFormat(self, fmt):
        self.resultFormat = fmt
    def add_tag(self, key, value, operator='=', condition='AND'):
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
    def add_select(self, sel_type, sel_params):
        if not { "params": sel_params, "type": sel_type } in select:
            self.select.append({ "params": sel_params, "type": sel_type })
            
    def add_groupBy(self, grp_type, grp_params):
        found = False
        for g in self.groupBy:
            if g["type"] == grp_type:
                g["params"] = grp_params
                found = True
        if not found:
            self.groupBy.append({'type': grp_type, 'params': grp_params})

class Tooltip(object):
    def __init__(self, shared=True, value_type="cumulative"):
        self.shared = shared
        self.value_type = value_type
    def set_shared(self, s):
        if isinstance(s, bool):
            self.shared = s
    def set_value_type(self, v):
        self.value_type = v
    def get(self):
        return {"shared" : self.shared, "value_type" : self.value_type}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())

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
        return str(self.get())

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

class TextPanel(Panel):
    def __init__(self, title="default title", mode="markdown", content="",
                       style={}, span=12, editable=True):
        Panel.__init__(self, span=span, editable=editable, title=title)
        self.set_mode(mode)
        self.content = content
        self.style = style
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
        return str(self.get())

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
    def __init__(self, maxValue=100, minValue=0, show=False, thresholdLabels=False, thresholdMarkers=True):
        self.maxValue = maxValue
        self.minValue = minValue
        self.show = show
        self.thresholdLabels = thresholdLabels
        self.thresholdMarkers = thresholdMarkers
    def get(self):
        return {"maxValue" : self.maxValue, "minValue" : self.minValue,
                "show" : self.show, "thresholdLabels" : self.thresholdLabels,
                "thresholdMarkers" :self.thresholdMarkers}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())

class Sparkline(object):
    def __init__(self, fillColor="rgba(31, 118, 189, 0.18)", full=False,
                       lineColor="rgb(31, 120, 193)", show=False):
        self.fillColor = check_color(fillColor)
        self.full = full
        self.lineColor = check_color(lineColor)
        self.show = show
    
    def get(self):
        return { "fillColor" : self.fillColor, "full" : self.full,
                 "lineColor" : self.lineColor, "show" : self.show }
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())

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
        if t in ["query", "interval", "custom"]:
            self.type = t
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

class Timepicker(object):
    def __init__(self, time_options=['5m', '15m', '1h', '6h', '12h', '24h', '2d', '7d', '30d'],
                       refresh_intervals=['5s', '10s', '30s', '1m', '5m', '15m', '30m', '1h', '2h', '1d']):
        self.time_options = time_options
        self.refresh_intervals = refresh_intervals
    
    def get(self):
        return {'time_options': self.time_options,
                'refresh_intervals': self.refresh_intervals}
    def get_json(self):
        return json.dumps(self.get())
    def __str__(self):
        return str(self.get())
    def __repr__(self):
        return str(self.get())

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
    def add_template(self, t):
        if isinstance(t, Template):
            x = copy.deepcopy(t)
            self.templates.append(x)
    def add_row(self, r):
        if isinstance(r, Row):
            x = copy.deepcopy(r)
            self.rows.append(x)
    def set_overwrite(self, b):
        if isinstance(b, bool):
            self.overwrite = b
    def set_editable(self, b):
        if isinstance(b, bool):
            self.editable = b
    def set_hideControls(self, b):
        if isinstance(b, bool):
            self.hideControls = b
    def set_sharedCrosshair(self, b):
        if isinstance(b, bool):
            self.sharedCrosshair = b
    def set_title(self, t):
        self.title = str(t)
    def set_originalTitle(self, t):
        self.originalTitle = str(t)
    def set_refresh(self, r):
        self.refresh = r
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
