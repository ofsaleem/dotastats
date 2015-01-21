Dota Records 1.0.1

Scrapes DOTABUFF for personal records of listed players and compares them to 
generate a personal high-score table.

Written by @onelivesleft, use as you will. Contact me there or at /u/-sideshow-

This is made for apache running mod_python, so you need that for it to work 
(though rewriting for some other python engine wouldn't be hard).

The cached.html file needs to have write permissions so that the program can 
save on top of it.  It will be used as long as it was generated within the last
two hours (or whatever timeframe you set in dota.py), otherwise dotabuff will 
be scraped and a new sheet page generated and stored.  If you add "?refresh=1"
to the URL it will force a refresh.

Edit the constants at the top of dota.py to set it up for yourself:  you *need*
to tell it the full server path to the cached.html file, and you need to change
the PLAYERS dictionary to your group of friends (or w/e).  The rest you can 
change or leave as you will.

Edit whatever image you want into the footer.png file, though if you change its
height you need to update the CSS to match (I think you'd be better just 
editting the blank footer.png file to what you want).