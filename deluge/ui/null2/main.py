#!/usr/bin/env python
import os, sys
import optparse
from deluge.ui.null2 import UI_PATH
from deluge.ui.null2.colors import Template, make_style, templates, default_style as style
from deluge.ui.client import aclient as client
import shlex
import logging

logging.disable(logging.ERROR)

class OptionParser(optparse.OptionParser):
    """subclass from optparse.OptionParser so exit() won't exit."""
    def exit(self, status=0, msg=None):
        self.values._exit = True 
        if msg:
            print msg

    def error(self, msg):
        """error(msg : string)

           Print a usage message incorporating 'msg' to stderr and exit.
           If you override this in a subclass, it should not return -- it
           should either exit or raise an exception.
        """
        raise


class BaseCommand(object):

    usage = 'usage'
    option_list = tuple()
    aliases = []


    def complete(self, text, *args):
        return []
    def handle(self, *args, **options):
        pass
    
    @property
    def name(self):
        return 'base'

    @property
    def epilog(self):
        return self.__doc__

    def split(self, text):
        return shlex.split(text)

    def _create_parser(self):
        return OptionParser(prog = self.name,
                            usage = self.usage,
                            epilog = self.epilog,
                            option_list = self.option_list)

def match_torrents(array=None):
    global torrents
    if array is None:
        array = list()
    torrents = []
    array = set(array)
    def _got_session_state(tors):
        if not array:
            torrents.extend(tors)
            return
        tors = set(tors)
        torrents.extend(list(tors.intersection(array)))
        return
    client.get_session_state(_got_session_state)
    client.force_call()
    return torrents

class NullUI(object):
    prompt = '>>> '

    def __init__(self, args=None):
        client.set_core_uri("http://localhost:58846")
        self._commands = self._load_commands()
        self._builtins = { 'help': self.help }
        self._all_commands = dict(self._commands)
        self._all_commands.update(self._builtins)

    def _load_commands(self):
        def get_command(name):
            return getattr(__import__('deluge.ui.null2.commands.%s' % name, {}, {}, ['Command']), 'Command')()

        command_dir = os.path.join(UI_PATH, 'commands')
        try:    
            commands = []
            for filename in os.listdir(command_dir):
                if filename.startswith('_') or not filename.endswith('.py'):
                    continue
                cmd = get_command(filename[:-3])
                aliases = [ filename[:-3] ]
                aliases.extend(cmd.aliases)
                for a in aliases:
                    commands.append((a, cmd))
            return dict(commands)
            #return dict([ (f[:-3], get_command(f[:-3])) for f in os.listdir(command_dir) if not f.startswith('_') and f.endswith('.py') ])
        except OSError, e:
            return {}

    def completedefault(self, *ignored):
        """Method called to complete an input line when no command-specific
        method is available.
    
        By default, it returns an empty list.
   
        """
        return []

    def completenames(self, text, *ignored):
        return [n for n in self._commands.keys() if n.startswith(text)]

    def complete(self, text, state):
        """Return the next possible completion for 'text'.
        If a command has not been entered, then complete against command list.
        Otherwise try to call complete_<command> to get list of completions.
        """
        if state == 0:
            import readline
            origline = readline.get_line_buffer()
            line = origline.lstrip()
            stripped = len(origline) - len(line)
            begidx = readline.get_begidx() - stripped
            endidx = readline.get_endidx() - stripped
            if begidx>0:
                cmd = line.split()[0]
                if cmd == '':
                    compfunc = self.completedefault
                else:
                    try:
                        compfunc = getattr(self._commands[cmd], 'complete')
                    except AttributeError:
                        compfunc = self.completedefault
            else:
                compfunc = self.completenames
            self.completion_matches = compfunc(text, line, begidx, endidx)
        try:
            return self.completion_matches[state]
        except IndexError:
            return None
                                                                                                                                                                                                                                                                                                                                                                            
    def preloop(self):
        pass

    def postloop(self):
        pass

    def precmd(self):
        pass

    def onecmd(self, line):
        if not line:
            return
        #v_line = line.split()
        cmd, _, line = line.partition(' ')
        if cmd in self._builtins:
            args = shlex.split(line)
            self._builtins[cmd](*args)
        else:
            try:
                parser = self._commands[cmd]._create_parser()
            except KeyError:
                print templates.ERROR('Error! unknown command: %s' % cmd)
                return
            args = self._commands[cmd].split(line)
            options, args = parser.parse_args(args)
            if not getattr(options, '_exit', False):
                try:
                    self._commands[cmd].handle(*args, **options.__dict__)
                except StopIteration, e:
                    raise
                except Exception, e:
                    print templates.ERROR(str(e))

    def postcmd(self):
        client.force_call()
        
    def _all_commands_keys_generator(self):
        return [ (self._commands, key) for key in self._commands] +\
                [ (self._builtins, key) for key in self._builtins]

    def help(self, *args):
        """displays this text"""
        usage = 'usage: help [command]'
        if args:
            if len(args) > 1:
                print usage
                return
            try:
                cmd = self._all_commands[args[0]]
            except KeyError:
                print templates.ERROR('unknown command %r' % args[0])
                return 
            try:
               parser = cmd.create_parser()
               print parser.format_help()
            except AttributeError, e:
                print cmd.__doc__ or 'No help for this command'
        else:
            max_length = max( len(k) for k in self._all_commands)
            for cmd in sorted(self._all_commands):
                print templates.help(max_length, cmd, self._all_commands[cmd].__doc__ or '')
        print 
        print 'for help on a specific command, use "<command> --help"'

    def cmdloop(self):
        self.preloop()
        try:
            import readline
            self.old_completer = readline.get_completer()
            readline.set_completer(self.complete)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

        while True:
            try:
                line = raw_input(templates.prompt(self.prompt)).strip()
            except EOFError:
                break
            except Exception, e:
                print e
                continue
            try:
                self.precmd()
                self.onecmd(line)
                self.postcmd()
            except StopIteration:
                break
        self.postloop()
        print
    run = cmdloop

if __name__ == '__main__':
    ui = NullUI()
    ui.precmd()
    ui.onecmd(' '.join(sys.argv[1:]))
    ui.postcmd()
