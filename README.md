Timeline
--------

The `Timeline` is a widget specialized for displaying time
information on a continuous, and perhaps infinite, scale. 
It inherits from `kivy.garden.tickline.Tickline` and thus allows
zooming in and out, and panning across time. Since `Timeline` works very
much like `kivy.garden.tickline.Tickline`, how 
`Timeline` works is fairly adequately covered 
in the `kivy.garden.tickline` package. 

Dependencies
============

1. kivy garden package `kivy.garden.tickline`. Use 
    ``garden install tickline`` to install it, just like installing any
    other garden package.

2. the ``pytz`` module for handling timezones. Use ``easy_install pytz`` or
    ``pip install pytz`` to install it for your python distribution.
    
3. for getting the local timezone, Windows or Unix-based systems need to get
   the ``tzlocal`` python module. ``easy_install`` or ``pip install`` should
   suffice here. 

Platforms
=========

Most of the code here work great regardless of platform. The only exception is
getting the local time zone.

With the above dependencies installed, this is not a problem for
desktop/laptop operating systems (Windows, Linux, OSX, etc). It should also
work on android, which is handled through ``pyjnius``'s ``autoclass``. 
However, it likely does NOT work in iOS. Currently
this is not a priority, but if you'd like to have this feature, you are welcome
to submit patches. 

Usage
=====

A simple timeline can be obtained by just calling

    timeline = Timeline()
    runTouchApp(timeline)
    
By default, the timeline will feature ticks with intervals of
 1 day, 4 hours, 1 hour, 15 minutes, 5 minutes, 1 minute, 15 seconds,
5 seconds, and 1 second which fills up the timeline adequately and not
overwhelmingly. It will center around the current time in the current timezone.

`Timeline` and `TimeTick` *is* timezone aware and is able to 
handle it by themselves in most cases. They by default use the local timezone
in the computation of times. 

Most of the customizable settings in `Timeline` are the same as
`~kivy.garden.tickline.Tickline`. These include 
`~Timeline.orientation`, `~Timeline.backward`, 
`~Timeline.line_offset`, `~Timeline.line_pos`, and
`~Timeline.min_scale`, `~Timeline.max_scale`. 

In addition, the attributes `Timeline.min_time`, `Timeline.max_time`,
`Timeline.time_0`, and `Timeline.time_1` are given as the time
versions of `~Timeline.min_index`, `~Timeline.max_index`,
`~Timeline.index_0`, and `~Timeline.index_1`.

The centerpiece of `Timeline`, though, is really `TimeTicks`s.
There are many available options for the intervals tracked, from 1 second to
1 day (the default ticks offer a sample of the them), listed in 
`TimeTick.mode_options`. You can change a `TimeTick`'s interval
by changing its `~TimeTick.mode`. For example

    # interval of 1 second
    tick = TimeTick(mode='second')
    # interval of 15 seconds
    tick = TimeTick(mode='15 seconds')
    # interval of 1 minute
    tick = TimeTick(mode='minute')
    # interval of 30 minutes
    tick = TimeTick(mode='30 minutes')
    
Most other attributes are inherited from `kivy.garden.tickline.Tick`.
These include `~TimeTick.tick_size`, `~TimeTick.label_global`,
`~TimeTick.halign`, `~TimeTick.valign`, etc.

You may use `selected_time_ticks` to get a list of `TimeTicks`s 
with intervals mentioned above. Or you can call `all_time_ticks` to get
a list of `TimeTick`s, one for each of available modes.

A more complex working example is

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
=========

The `TimeTick` overrides `Tick.tick_iter`
to yield datetimes instead of local indices, and `Tick.draw` similarly
expects datetimes instead of indices. Hence for most graphics customization, 
overriding `TimeTick.draw` may be enough. For example, a time series
grapher can override `TimeTick.draw` to draw a dot at the height 
corresponding to the given datetime. 

Of course, the labeller `TimeLabeller` can also be subclassed or
ducktyped to provide the necessary functionality.
