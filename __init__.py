'''
Timeline
========

The :class:`Timeline` is a widget specialized for displaying time
information on a continuous, and perhaps infinite, scale. 
It inherits from :class:`kivy.garden.tickline.Tickline` and thus allows
zooming in and out, and panning across time. Since :class:`Timeline` works very
much like :class:`kivy.garden.tickline.Tickline`, how 
:class:`Timeline` works is fairly adequately covered 
in the :mod:`kivy.garden.tickline` package. 

Dependencies
------------

1. kivy garden package :mod:`kivy.garden.tickline`. Use 
    ``garden install tickline`` to install it, just like installing any
    other garden package.

2. the ``pytz`` module for handling timezones. Use ``easy_install pytz`` or
    ``pip install pytz`` to install it for your python distribution.
    
3. for getting the local timezone, Windows or Unix-based systems need to get
   the ``tzlocal`` python module. ``easy_install`` or ``pip install`` should
   suffice here. 

Platforms
---------

Most of the code here work great regardless of platform. The only exception is
getting the local time zone.

With the above dependencies installed, this is not a problem for
desktop/laptop operating systems (Windows, Linux, OSX, etc). It should also
work on android, which is handled through ``pyjnius``'s ``autoclass``. 
However, it likely does NOT work in iOS. Currently
this is not a priority, but if you'd like to have this feature, you are welcome
to submit patches. 

Usage
-----

A simple timeline can be obtained by just calling::

    timeline = Timeline()
    runTouchApp(timeline)
    
By default, the timeline will feature ticks with intervals of
 1 day, 4 hours, 1 hour, 15 minutes, 5 minutes, 1 minute, 15 seconds,
5 seconds, and 1 second which fills up the timeline adequately and not
overwhelmingly. It will center around the current time in the current timezone.

:class:`Timeline` and :class:`TimeTick` *is* timezone aware and is able to 
handle it by themselves in most cases. They by default use the local timezone
in the computation of times. 

Most of the customizable settings in :class:`Timeline` are the same as
:class:`~kivy.garden.tickline.Tickline`. These include 
:attr:`~Timeline.orientation`, :attr:`~Timeline.backward`, 
:attr:`~Timeline.line_offset`, :attr:`~Timeline.line_pos`, and
:attr:`~Timeline.min_scale`, :attr:`~Timeline.max_scale`. 

In addition, the attributes :attr:`Timeline.min_time`, :attr:`Timeline.max_time`,
:attr:`Timeline.time_0`, and :attr:`Timeline.time_1` are given as the time
versions of :attr:`~Timeline.min_index`, :attr:`~Timeline.max_index`,
:attr:`~Timeline.index_0`, and :attr:`~Timeline.index_1`.

The centerpiece of :class:`Timeline`, though, is really :class:`TimeTicks`s.
There are many available options for the intervals tracked, from 1 second to
1 day (the default ticks offer a sample of the them), listed in 
:attr:`TimeTick.mode_options`. You can change a :class:`TimeTick`'s interval
by changing its :attr:`~TimeTick.mode`. For example::

    # interval of 1 second
    tick = TimeTick(mode='second')
    # interval of 15 seconds
    tick = TimeTick(mode='15 seconds')
    # interval of 1 minute
    tick = TimeTick(mode='minute')
    # interval of 30 minutes
    tick = TimeTick(mode='30 minutes')
    
Most other attributes are inherited from :class:`kivy.garden.tickline.Tick`.
These include :attr:`~TimeTick.tick_size`, :attr:`~TimeTick.label_global`,
:attr:`~TimeTick.halign`, :attr:`~TimeTick.valign`, etc.

You may use :func:`selected_time_ticks` to get a list of :class:`TimeTicks`s 
with intervals mentioned above. Or you can call :func:`all_time_ticks` to get
a list of :class:`TimeTick`s, one for each of available modes.

A more complex working example is::

    if __name__ == '__main__':
        acc = Accordion(orientation='vertical')
        simple = AccordionItem(title='simple')
        simple.add_widget(Timeline())
        complex_ = AccordionItem(title='complex')
        complex_.add_widget(
            Timeline(backward=True,
                     orientation='horizontal',
                     ticks=(selected_time_ticks() + 
                             [TimeTick(valign='top',
                                       mode='12 hours'),
                              TimeTick(valign='line_bottom',
                                       mode='2 hours')]),
                     line_offset=dp(130)
                     ))
        acc.add_widget(simple)
        acc.add_widget(complex_)
        runTouchApp(acc)

Extending
---------

The :class:`TimeTick` overrides :meth:`Tick.tick_iter`
to yield datetimes instead of local indices, and :meth:`Tick.draw` similarly
expects datetimes instead of indices. Hence for most graphics customization, 
overriding :meth:`TimeTick.draw` may be enough. For example, a time series
grapher can override :meth:`TimeTick.draw` to draw a dot at the height 
corresponding to the given datetime. 

Of course, the labeller :class:`TimeLabeller` can also be subclassed or
ducktyped to provide the necessary functionality.

'''
from bisect import bisect, bisect_left
from datetime import datetime, timedelta
from decimal import DivisionByZero
from itertools import chain
from kivy.base import runTouchApp
from kivy.core.text import Label as CoreLabel
from kivy.event import EventDispatcher
from kivy.garden.tickline import TickLabeller, Tick, Tickline
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import Rectangle, Line
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, OptionProperty, \
    DictProperty, ObjectProperty, BoundedNumericProperty, BooleanProperty, \
    AliasProperty
from kivy.uix.accordion import AccordionItem, Accordion
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from math import ceil, floor
from numbers import Number
from pytz import UTC

try:
    from tzlocal import get_localzone
except ImportError:
    from jnius import autoclass
    from pytz import timezone
    TimeZone = autoclass('java.util.TimeZone')
    
    def get_localzone():
        return timezone(TimeZone.getDefault().getID())
    
def local_now():
    return get_localzone().localize(datetime.now())    

Builder.load_string('''
<AutoSizeLabel>:
    size: self.texture_size
    size_hint: None, None
''')
class AutoSizeLabel(Label):
    pass

class TimeLabeller(TickLabeller):
    '''default labeller of :class:`Timeline`. For an example of its graphics,
    see example images or run the example in the module documentation.
    '''
    
    date_halign = OptionProperty('left', options=['left', 'right'])   
    '''specifies whether the date labels are on the left or right side of
    the :class:`Timeline` when the timeline is vertical. Has no effect when
    the timeline is horizontal.'''
    
    date_valign = OptionProperty('bottom', options=['top', 'bottom'])
    '''specifies whether the date labels are on top or bottom of
    the :class:`Timeline` when the timeline is horizontal. Has no effect when
    the timeline is vertical.'''

    time_halign = OptionProperty('left', options=['left', 'right'])   
    '''specifies whether the time labels are on the left or right side of
    the :class:`Timeline` when the timeline is vertical. Has no effect when
    the timeline is horizontal.'''

    time_valign = OptionProperty('bottom', options=['top', 'bottom'])
    '''specifies whether the time labels are on top or bottom of
    the :class:`Timeline` when the timeline is horizontal. Has no effect when
    the timeline is vertical.'''

    date_dist_from_edge = NumericProperty('55dp')
    '''distance of the date labels from the edge of the :class:`Timeline`.'''
    
    time_dist_from_edge = NumericProperty('22dp')
    '''distance of the time labels from the edge of the :class:`Timeline`.'''

    date_font_size = NumericProperty('12sp')
    '''font size of the date labels.'''

    time_font_size = NumericProperty('7sp')
    '''font size of the time labels.'''
    
    def __init__(self, tickline, **kw):
        super(TimeLabeller, self).__init__(tickline, **kw)
        self.labels = []
        self.seconds_registrar = {}
        self.have_time = False
        self.instructions = {}
        
    def re_init(self, *args):
        self.labels = []
        self.seconds_registrar = {}
        self.have_time = False
        super(TimeLabeller, self).re_init(*args)
        
    def register(self, tick, tick_index, tick_info):
        assert isinstance(tick_index, Number)
        tick_sc = tick.scale(self.tickline.scale)
        if tick_sc < tick.min_label_space:
            return
        seconds = tick.to_seconds(tick_index)
        if self.seconds_registrar.get(seconds, 0) < tick_sc:
            self.have_time |= tick.mode != 'day'
            self.registrar.setdefault(tick, {})[tick_index] = tick_info
            self.seconds_registrar[seconds] = tick_sc
            
    def _get_texture_pos(self, tick, index, succinct=True, which='time',
                         texture=None):
        tl = self.tickline
        # tick_info should be (x, y, width, height) of tick
        tick_info = self.registrar[tick][index]
        if not texture:
            label_kw = tick.get_label_texture(index, succinct, return_kw=True)
            if not label_kw:
                return
            label_kw['font_size'] = self.time_font_size if which == 'time' else \
                                      self.date_font_size
            label_kw['halign'] = 'left' if tl.is_vertical() else 'center'
            label = CoreLabel(**label_kw)
            label.refresh()
            texture = label.texture
        if tl.is_vertical():
            y = tick_info[1] + tick_info[3] / 2 - texture.height / 2
            if which == 'time':
                dist = self.time_dist_from_edge
            else:
                dist = self.date_dist_from_edge            
            dist = max(dist, tick.tick_size[1] + tl.tick_label_padding)
            halign = tick.halign
            if halign == 'left':
                x = tl.x + dist
            elif halign == 'line_left':
                x = tl.line_pos - dist - texture.width
            elif halign == 'line_right':
                x = tl.line_pos + dist
            else:
                x = tl.right - dist - texture.width
        else:
            # TODO horizontal is gonna get crowded with text
            x = tick_info[0] + tick_info[2] / 2 - texture.width / 2
            if which == 'time':
                dist = self.time_dist_from_edge
            else:
                dist = self.date_dist_from_edge
            dist = max(dist, tick.tick_size[1] + tl.tick_label_padding)
            valign = tick.valign
            if valign == 'top':
                y = tl.top - dist - texture.height
            elif valign == 'line_top':
                y = tl.line_pos + dist
            elif valign == 'line_bottom':
                y = tl.line_pos - dist - texture.height
            else:
                y = tl.y + dist       
        return (texture, [x, y])
    def make_labels(self):
        r = self.registrar
        instructions = self.instructions
        setdefault = instructions.setdefault
        to_pop = set((tick, index) for tick in instructions 
                  for index in instructions[tick])
        tl = self.tickline
        succinct = not any('second' in tick.mode for tick in r)
        get_texture_pos = self._get_texture_pos
        canvas = tl.canvas
        for tick in r:
            instrs = setdefault(tick, {})
            if tick.mode != 'day':
                for index in r[tick]:
                    self._update_rect(tick, index, instrs, get_texture_pos,
                                      to_pop, succinct, canvas)
            else:
                a = tl.is_vertical()
                b = 1 - a
                bottom_up = sorted(r[tick], reverse=tl.backward)
                if self.have_time:
                    last_rect = [None, None]
                    for index in bottom_up:
                        rect = \
                        self._update_rect(tick, index, instrs, get_texture_pos,
                                          to_pop, succinct, canvas, which='date')
                        last_rect[0] = last_rect[1]
                        last_rect[1] = rect
                                                   
                    max_ = tl.top if a else tl.right
                    if len(bottom_up) > 1:
                        _2ndlast, last = last_rect
                        last_coord = max(_2ndlast.pos[a] + _2ndlast.size[a],
                                     max_ - last.size[a])
                        _2ndlast_coord = min(_2ndlast.pos[a] + _2ndlast.size[a],
                                         max_) - _2ndlast.size[a]
                        last.pos = (last.pos[b], last_coord) if a else \
                                    (last_coord, last.pos[b])
                        _2ndlast.pos = (_2ndlast.pos[b], _2ndlast_coord) if a \
                                        else (_2ndlast_coord, _2ndlast.pos[b])
                    else:
                        new_coord = max_ - last_rect[1].size[a]
                        last_rect[1].pos = (last_rect[1].pos[b], new_coord) \
                                            if a else \
                                            (new_coord, last_rect[1].pos[b])
                else:
                    for index in bottom_up[:-1]:
                        self._update_rect(tick, index, instrs, get_texture_pos,
                                          to_pop, succinct, canvas, which='date')
        for tick, index in to_pop:
            rect = instructions[tick].pop(index)
            canvas.remove(rect)
             
    def _update_rect(self, tick, index, instrs, get_texture_pos, to_pop,
                     succinct, canvas, which='time'):
        if index in instrs:
            # old label: change position
            old_rect = instrs[index]
            t_p = get_texture_pos(tick, index, succinct,
                                  texture=old_rect.texture, which=which)
            old_rect.pos = t_p[1]
            to_pop.remove((tick, index))
            return old_rect
        else:
            # new label
            t_p = get_texture_pos(tick, index, succinct, which=which) 
            if t_p:
                texture, pos = t_p
                rect = Rectangle(texture=texture, pos=pos,
                                 size=texture.size)
                instrs[index] = rect
                canvas.add(rect)
                return rect
                        
        
unixepoch = datetime(1970, 1, 1, tzinfo=UTC)


_tail_names = ['microsecond', 'second', 'minute', 'hour', 'day']
_tail_res = {'microsecond': 10 ** -6, 'second': 1, 'minute': 60, 'hour': 3600,
             'day': 3600 * 24}

def time_tail(dt, length=2, tail_name=None, strict=False):
    '''given a datetime ``dt``, gives its time tail specified by ``length``
    or ``tail_name``::
    
        >>> assert(
            time_tail(datetime(2010, 10, 4, 13, 25, 5, 0.33)) ==
            timedelta(seconds=5.33))
        >>> assert(
            time_tail(datetime(2010, 10, 4, 13, 25, 5, 0.33), 3) ==
            timedelta(minutes=25, seconds=5.33))
        >>> assert(
            time_tail(datetime(2010, 10, 4, 13, 25, 5, 0.33), 
                tail_name='hour') ==
            timedelta(hour=13, minute=25, second=5.33))
        >>> assert(
            time_tail(datetime(2010, 10, 4, 13, 25, 5, 0.33), 
                tail_name='hour', strict=True) ==
            timedelta(minute=25, second=5.33))
    '''
    if tail_name:
        length = _tail_names.index(tail_name) + 1 - strict
    timedelta_kw = {}
    for name in _tail_names[:length]:
        timedelta_kw[name + 's'] = getattr(dt, name)
    return timedelta(**timedelta_kw)

def set_time_tail(dt, time_vector=[0]):
    for name, val in zip(_tail_names, time_vector):
        setattr(dt, name, val)
        
def round_time(dt, grain='second', mode='nearest'):
    '''round datetime ``dt`` to the nearest, next, or previous second, 
    15 seconds, minutes, etc::
    
        >>> round_time(datetime(2013, 2, 3, 5, 23, 56), 'minute', 'nearest')
        datetime.datetime(2013, 2, 3, 5, 24, 0)
        >>> round_time(datetime(2013, 2, 3, 5, 23, 56), 'minute', 'down')
        datetime.datetime(2013, 2, 3, 5, 23, 0)
        >>> round_time(datetime(2013, 2, 3, 5, 23, 56), 'day', 'up')
        datetime.datetime(2013, 2, 4, 0, 0, 0)
        
    :param dt: datetime object to round
    :param grain: the smallest granularity to round toward. Can be any of
        :attr:`TimeTick.mode`. Defaults to 'second'
    :param mode: the rounding mode. Can be any one of 'nearest', 'up', or 'down'.
        Defaults to 'nearest'
    '''
    if mode == 'nearest':
        round_func = round
    elif mode == 'up':
        round_func = ceil
    else:
        round_func = floor
    res = TimeTick.granularity(grain)
    if grain in _tail_names:
        tail = time_tail(dt, _tail_names.index(grain))
    else:
        mult, gr = grain.split(' ')
        tail = time_tail(dt, _tail_names.index(gr[:-1]) + 1)
    trunced = dt - tail
    return timedelta(seconds=res * round_func(tail.total_seconds() / res)) \
        + trunced


class TimeTick(Tick):  
    
    size_dict = \
        {'day': [dp(5), dp(48)],
         '12 hours': [dp(4.5), dp(25)],
         '6 hours': [dp(4.5), dp(25)],
         '4 hours': [dp(4), dp(20)],
         '2 hours': [dp(4), dp(20)],
         'hour': [dp(4), dp(20)],
         '30 minutes': [dp(3), dp(12)],
         '15 minutes': [dp(3), dp(12)],
         '10 minutes': [dp(2), dp(8)],
         '5 minutes': [dp(2), dp(8)],
         'minute': [dp(2), dp(8)],
         '30 seconds': [dp(1.5), dp(7)],
         '15 seconds': [dp(1.5), dp(7)],
         '10 seconds': [dp(1), dp(4)],
         '5 seconds': [dp(1), dp(4)],
         'second': [dp(1), dp(4)]} 
        
    scale_factor_dict = \
        {'day': 1,
         '12 hours': 2,
         '6 hours': 4,
         '4 hours': 6,
         '2 hours': 12,
         'hour': 24,
         '30 minutes': 48,
         '15 minutes': 96,
         '10 minutes': 48 * 3,
         '5 minutes': 3 * 96,
         'minute': 24 * 60,
         '30 seconds': 24 * 120,
         '15 seconds': 24 * 240,
         '10 seconds': 24 * 360,
         '5 seconds': 24 * 720,
         'second': 24 * 3600}
        
    mode_options = ['day',
           '12 hours',
           '6 hours',
           '4 hours',
           '2 hours',
           'hour',
           '30 minutes',
           '15 minutes',
           '10 minutes',
           '5 minutes',
           'minute',
           '30 seconds',
           '15 seconds',
           '10 seconds',
           '5 seconds',
           'second']
    
    mode = OptionProperty('day', options=mode_options)
    # 188 is good to be an entire header for the date
    _tick_size = ListProperty(None)
    def get_tick_size(self, *args):
        return self._tick_size or self.size_dict[self.mode]
    def set_tick_size(self, val):
        self._tick_size = val
    tick_size = AliasProperty(get_tick_size, set_tick_size,
                              bind=['_tick_size', 'mode'])
    tz = ObjectProperty(get_localzone())
    def __init__(self, *args, **kw):
        super(TimeTick, self).__init__(*args, **kw)
    @classmethod
    def granularity(cls, mode):
        '''gives the multiplicity of this mode in terms of seconds.'''
        return cls.scale_factor_dict['second'] / cls.scale_factor_dict[mode]
    def time_min_max(self, tl, extended=False):
        '''gives either (:meth:`time_0`, :meth`time_1`) or 
        (:meth:`time_1`, :meth`time_0`) applied to ``tl``
        so that the first time is not later than the second. In essence,
        provide the minimal and maximal time that can be shown on the screen
        at the time of method call.
        
        If ``extended``, then time corresponding 1 ``tl.densest_tick``
        below and 1 above the current window will be given instead.
        
        :param tl: :class:`Tickline` instance.
        :param extended: If True, gives a slightly larger window, as discussed
            above. Defaults to False.
        '''
        
        min_, max_ = (tl.time_1, tl.time_0) if tl.backward else \
                        (tl.time_0, tl.time_1)
                    
        if extended:
            interval = TimeTick.granularity(tl.densest_tick.mode)
            min_ -= timedelta(seconds=interval)
            max_ += timedelta(seconds=interval)
        return min_, max_
        
    def tick_iter(self, tl):
        '''Overrides :meth:`Tick.tick_iter`.
        
        Provides an iterator of the times that correspond to ticks that 
        should be drawn on screen, depending on :attr:`mode`. Note that
        for the "day" mode, the day past the last day shown on screen is also
        given, for the push graphics (see :class:`TimeLabeller` for details).
        '''
        if self.scale(tl.scale) < self.min_space:
            raise StopIteration        
        time_min, time_max = self.time_min_max(tl, extended=True)
        time = round_time(time_min, self.mode, 'up')
        delta = timedelta(seconds=self.granularity(self.mode))
        if self.mode == 'day' and tl.backward:
            yield time - timedelta(days=1)
        while time <= time_max:
            yield time
            time += delta
        if self.mode == 'day' and not tl.backward:
            yield time
        raise StopIteration
    
    def draw(self, tickline, time):
        '''Override :meth:`Tick.draw`.
        
        Instead of taking a pair (pos, index) of the tick to be drawn, takes
        the time of such a tick, and internally convert it to (pos, index)
        using :meth:`index_of` and :meth:`index2pos`.
        '''
        super(TimeTick, self).draw(tickline, self.pos_index_of(tickline, time))
        
    def pos_index_of(self, tickline, time):
        tick_index = self.index_of(time)
        tick_pos = tickline.index2pos(self.globalize(tick_index))
        return tick_pos, tick_index
    
    def pos_of(self, tickline, time):
        return self.pos_index_of(tickline, time)[0]
    
    def on_mode(self, *args):
        self.scale_factor = self.scale_factor_dict[self.mode]
        
    def datetime_of(self, tick_index):
        if self.mode in ('day', 'hour', 'minute', 'second'):
            t = timedelta(**{self.mode + 's': tick_index}) + unixepoch
        else:
            mult, mode = self.mode.split(' ')
            t = timedelta(**{mode: int(mult) * tick_index}) + unixepoch
        t = t.astimezone(self.tz)
        return t
    
    def to_seconds(self, tick_index):
        '''converts the ``tick_index`` to the number of seconds since 
        unix epoch. Always returns the nearest integer.'''
        
        return round(tick_index * self.scale_factor_dict['second'] 
                     / self.scale_factor)
        
    def pos2time(self, pos, tl):
        return self.datetime_of(self.localize(tl.pos2index(pos)))

    def index_of(self, dt, global_=False):
        '''return a local index corresponding to a datetime. If ``global_``
        is true, then return the global index (the index of the owning 
        :class:`Tickline`).
        
        :param dt: a datetime to be converted to index.
        :param global_: flag that indicates the index returned should be global.
            Defaults to False.
        '''
        
        secs = (dt - unixepoch).total_seconds() 
        global_idx = secs / self.scale_factor_dict['second']
        if global_:
            return global_idx
        return self.localize(global_idx)
            
    def get_label_texture(self, index, succinct=True, return_kw=False,
                          return_label=False, **kw):
        if isinstance(index, Number):
            t = self.datetime_of(index)
        else:
            t = index
        if self.mode == 'second':
            return None
        if self.mode == 'day':
            # need to get the datetime of the previous day
            text = (t - timedelta(seconds=1)).strftime('%a\n%m-%d-%y')
            kw.setdefault('height', 50)
        elif 'second' not in self.mode and succinct:
            text = str(t.time())[:-3]
        else:
            text = str(t.time())
        kw.setdefault('height', 20)
        kw['text'] = text
        if return_kw:
            return kw
        if not return_label:
            return CoreLabel(**kw).texture
        label = AutoSizeLabel(**kw)
        label.texture_update()
        return label
    
def all_time_ticks():
    '''returns a list of :class:`TimeTick`s, one for each of the available
    :attr:`~TimeTick.mode`s, specified in :attr:`TimeTick.mode_options`.
    '''
    return [TimeTick(mode=m) for m in TimeTick.mode.options]

def selected_time_ticks():
    '''returns a list of :class:`TimeTick`s with intervals of
    1 day, 4 hours, 1 hour, 15 minutes, 5 minutes, 1 minute, 15 seconds,
    5 seconds, and 1 second.'''
    return [TimeTick(mode=TimeTick.mode.options[i]) for i in 
            [0, 3, 5, 7, 9, 10, 12, 14, 15]]
    
class Timeline(Tickline):
    '''subclass of :class:`Tickline` specialized for displaying time 
    information. See module documentation for more details.'''
    
    labeller_cls = ObjectProperty(TimeLabeller)
    
    tz = ObjectProperty(get_localzone())
    
    def get_min_time(self, *args):
        return self.datetime_of(self.min_index)
    def set_min_time(self, val):
        self.min_index = self.index_of(val)
    min_time = AliasProperty(get_min_time, set_min_time, cache=True,
                             bind=['min_index'])
    '''the minimal time beyond which this :class:`Timeline` cannot go.
    This is a time version of :attr:`Tickline.min_index`.'''
    
    def get_max_time(self, *args):
        return self.datetime_of(self.max_index)
    def set_max_time(self, val):
        self.max_index = self.index_of(val)
    max_time = AliasProperty(get_max_time, set_max_time, cache=True,
                             bind=['max_index'])
    '''the maximal time beyond which this :class:`Timeline` cannot go.
    This is a time version of :attr:`Tickline.max_index`.'''
        
    def get_time_0(self, *args):
        return self.datetime_of(self.index_0)
    def set_time_0(self, val):
        self.index_0 = self.datetime_of(val)
    time_0 = AliasProperty(get_time_0, set_time_0,
                           bind=['index_0'])  
    '''gives the time that that sits on top of
    ``self.x`` if :attr:`orientation` is 'vertical', or ``self.y``
    if :attr:`orientation` is 'horizontal'. Note that this doesn't 
    depend on :attr:`Tickline.backward`.
    
    This is the time version of :class:`Tickline.index_0`.'''    
    
    def get_time_1(self, *args):
        return self.datetime_of(self.index_1)
    def set_time_1(self, val):
        self.index_1 = self.datetime_of(val)
    time_1 = AliasProperty(get_time_1, set_time_1,
                           bind=['index_1'])  
    '''gives the time that that sits on top of
    ``self.right`` if :attr:`orientation` is 'vertical', or ``self.top``
    if :attr:`orientation` is 'horizontal'. Note that this doesn't 
    depend on :attr:`Tickline.backward`.
    
    This is the time version of :class:`Tickline.index_1`.'''       

    def __init__(self, **kw):
        now = local_now().astimezone(UTC)
        self.center_on_timeframe(now - timedelta(days=1),
                                 now + timedelta(days=1))
        self.ticks = selected_time_ticks()
        super(Timeline, self).__init__(**kw)
    def on_tz(self, *args):
        for tick in self.ticks:
            tick.tz = self.tz
    def pos2time(self, pos):
        return self.datetime_of(self.pos2index(pos))
    def datetime_of(self, index):
        return (timedelta(days=index) + unixepoch).astimezone(self.tz)
    def index_of(self, dt):
        '''return a global index corresponding to a datetime. '''
        secs = (dt - unixepoch).total_seconds() 
        global_idx = secs / TimeTick.scale_factor_dict['second']
        return global_idx
    def pos_of_time(self, time):
        return self.index2pos(self.index_of(time))
    def timedelta2dist(self, td):
        return td.days * self.scale
    def center_on_timeframe(self, start, end):
        self.index_0 = self.index_of(start)
        self.index_1 = self.index_of(end)
                
if __name__ == '__main__':
    acc = Accordion(orientation='vertical')
    simple = AccordionItem(title='simple')
    simple.add_widget(Timeline())
    complex_ = AccordionItem(title='complex')
    complex_.add_widget(
        Timeline(backward=True,
                 orientation='horizontal',
                 ticks=selected_time_ticks() + [TimeTick(valign='top',
                                                         mode='12 hours'),
                                                TimeTick(valign='line_bottom',
                                                         mode='2 hours')],
                 line_offset=dp(130)
                 ))
    acc.add_widget(simple)
    acc.add_widget(complex_)
    runTouchApp(acc)

