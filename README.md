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
<strike>Eg, to listen on port 4321 for any IPv6 address, enter: `[::]:4321`</strike>  
By [code inspection](https://github.com/videolan/vlc/blob/master/modules/control/oldrc.c#L301-L306),
I see that vlc now parses this input as a URL.  So enter: `tcp://:4321/`

Invoke this script with: `vlc-control -s my-vlc-server.hostname.example.org:4321`

### Examples

#### VLC: Persistent configuration

Launch VLC, open Preferences (`⌘-,` on macOS), click "Show All"; on the left,
expand "Interfaces", "Main Interfaces", enable the "Remote control interface"
checkbox (which will add `oldrc` to the viewable list of interfaces just above
the checkboxes).  Then on the left, click "RC" and in the new control tab, for
"TCP command input", enter the URL for listening.

Enter `tcp://127.0.0.1:4321/` to listen on all IPs on the localhost, which is
safest but does raise the question of "why", with other controls available.

Enter `tcp://:4321/` to listen on all IPs on port 4321, which will allow
anyone who can reach you over the network to control VLC without
authentication.  Possibly useful on trusted networks to control a mini playing
onto a nice screen, or when another laptop is hooked up to a TV.

Then use `vlc-control.py -s 127.0.0.1:4321`, for remote hosts replacing the
loopback IP with whatever hostname is needed to reach the running instance of
VLC.

#### VLC: Non-persistent, CLI enabling

The above shows us that `oldrc` is an "extra interface", not an "interface",
so we want the `--extraintf` parameter, not `-I`.
Using `vlc -p oldrc --advanced` we can see the available options.
Thus:

```console
$ vlc --extraintf=oldrc --rc-host tcp://127.0.0.1:4321/ "$filename"
```


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

