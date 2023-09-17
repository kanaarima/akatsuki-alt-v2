import front.commands.documentation.link as link
import front.commands.documentation.setdefault as setdefault
import front.commands.documentation.recent as recent
import front.commands.documentation.show as show
import front.commands.documentation.reset as reset
import front.commands.documentation.show1s as show1s
import front.commands.documentation.showclears as showclears
import front.commands.documentation.showcompletion as showcompletion
import front.commands.documentation.show1slb as show1slb
import front.commands.documentation.getfile as getfile


help_dict = {
    "link": link.title,
    "setdefault": setdefault.title,
    "recent": recent.title,
    "show": show.title,
    "reset": reset.title,
    "show1s": show1s.title,
    "showclears": showclears.title,
    "showcompletion": showcompletion.title,
    "show1slb": show1slb.title,
    "getfile": getfile.title,
}

help = "\n".join(list(help_dict.values()))
help_full = {
    "link": link.documentation,
    "setdefault": setdefault.documentation,
    "recent": recent.documentation,
    "show": show.documentation,
    "reset": reset.documentation,
    "show1s": show1s.documentation,
    "showclears": showclears.documentation,
    "showcompletion": showcompletion.documentation,
    "show1slb": show1slb.documentation,
    "getfile": getfile.documentation,
}
