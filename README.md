vlc-control
===========

Remote control of VLC, from another computer, which can handle DVD navigation
via cursor-keys and Enter, plus a few more things.

The bits missing from the web UI!


Setup
-----

This script is written to Python 3.2 and uses curses.  It expects a UTF-8
locale for some of the characters printed.

It has been tested on MacOS.  OS success/failure reports welcome.

Turn on the "RC" interface (also called "OLDRC") in VLC.
Set an IP address and port to listen on in VLC's preferences.
Eg, to listen on port 4321 for any IPv6 address, enter: `[::]:4321`

Invoke this script with: `vlc-control -s my-vlc-server.hostname.example.org:4321`


Limitations
-----------

No file-selection or browsing UI: I still use the web UI for that.
Patches welcome.

Shift-\<digit\> assumes US keyboard layout.


Problems
--------

I am experimenting with use of gerrithub.io for pull requests and reviews in
this repository:

* <https://review.gerrithub.io/#/q/project:philpennock/vlc-control,n,z>
* Clone, anonymous HTTP: <https://review.gerrithub.io/philpennock/vlc-control>
* SSH Push URL: <ssh://review.gerrithub.io:29418/philpennock/vlc-control>
  (requires account)

<del>
I accept pull requests and issue reports via the github interfaces for such.

<https://github.com/philpennock/vlc-control/>
</del>

