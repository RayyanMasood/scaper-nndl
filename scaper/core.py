

import sox, random, glob, os, warnings, jams
import pandas as pd

class Scaper(object):

    def __init__(self, fg_path, bg_path, fg_class, bg_class, num_scapes=1, snr=10, duration=10, fg_start=1, bg_start=1):
        """

        Parameters
        ----------

        fg_path:    path to foreground audio
        bg_path:    path to background soundscape audio
        fg_class:   background class
        fg_class:   foreground class
        num_scapes: number of soundscapes to generate
        snr:        signal to noise ratio
        duration:   duration of output file

        """

        self.MAX_DB = -3

        # THESE PROBABLY CAN BE None, Specific, Multiple
        self.bg_class = bg_class
        self.fg_class = fg_class
        self.num_scapes = num_scapes
        self.fg_path = fg_path              # foregrounds
        self.bg_path = bg_path              # backgrounds

        self.duration = duration
        self.fg_start = fg_start
        self.bg_start = bg_start

        self.events = None
        self.snr = snr

        files = []
        bit_rates = []
        num_channels = []
        samp_rates = []

        # rename audio files to exclude space and comma chars
        self.rename_files(self.fg_path)
        self.rename_files(self.bg_path)

        self.fgs = pd.DataFrame(columns=['file_name', 'bit_rate', 'num_channels', 'sample_rate'])
        self.bgs = pd.DataFrame(columns=['file_name', 'bit_rate', 'num_channels', 'sample_rate'])

        # foreground file lists
        for file in glob.glob(self.fg_path+"/"+fg_class+"/*"):
            files.append(file)
            bit_rates.append(sox.file_info.bitrate(file))
            num_channels.append(sox.file_info.channels(file))
            samp_rates.append(sox.file_info.sample_rate(file))

        # create event list
        self.fgs['file_name'] = files
        self.fgs['bit_rate'] = bit_rates
        self.fgs['num_channels'] = num_channels
        self.fgs['sample_rate'] = samp_rates

        # clear these data structures
        files = []
        bit_rates = []
        num_channels = []
        samp_rates = []

        # background file lists
        for file in glob.glob(self.bg_path+"/"+bg_class+"/*"):
            files.append(file)
            bit_rates.append(sox.file_info.bitrate(file))
            num_channels.append(sox.file_info.channels(file))
            samp_rates.append(sox.file_info.sample_rate(file))

        # create event lists
        self.bgs['file_name'] = files
        self.bgs['bit_rate'] = bit_rates
        self.bgs['num_channels'] = num_channels
        self.bgs['sample_rate'] = samp_rates


    def generate_jams(self, list, type, jams_outfile):

        # for generating jams files of input and ouput files
        if type == 'file':
            file_jam = jams.JAMS()
            file_ann = jams.Annotation(namespace='tag_open')

            # everything goes into the value field as a tuple
            for ind, event in list.iterrows():
                file_ann.append(time=0, duration=1.0,
                                 value=(list['file_name'], list['bit_rate'],
                                        list['num_channels'], list['sample_rate']),
                                 confidence=1)

            # add annotation to jams file
            file_jam.annotations.append(file_ann)
            # dummy duration
            file_jam.file_metadata.duration = 1
            file_jam.save('./file_out.jams')

            print file_ann.data
            # file_jam.save(jams_outfile)

        # for generating jam files of scene
        elif type == 'scape':
            scene_jam = jams.JAMS()
            scene_ann = jams.Annotation(namespace='tag_open')

            # everything goes into the value field as a tuple
            for ind, event in list.iterrows():
                print list['label'][ind]
                scene_ann.append(time=list['start_time'][ind],
                                 duration=list['end_time'][ind] - list['start_time'][ind],
                                 value=(list['label'][ind], list['src_file'][ind],
                                        list['src_start'][ind], list['src_end'][ind],
                                        list['snr'][ind], list['role'][ind]),
                                 confidence=1)

            # add annotation to jams file
            scene_jam.annotations.append(scene_ann)

            print scene_ann.data


            print '\n'
            scene_jam.file_metadata.duration = (list['end_time'][ind] - list['start_time'][ind])
            # scene_jam.save('./scene_out.jams')



    def normalize_file(self, file, max_db, out_file):

        """

        Parameters
        ----------
        file :      file to normalize
        max_db:     normalize reference
        out_file:   file to save normalized output

        """

        nrm = sox.Transformer(file, out_file)
        nrm.norm(max_db)
        return nrm


    def rename_files(self, path):

        """

        Parameters
        ----------
        path: path to files for renaming

        """
        paths = (os.path.join(root, filename)
                 for root, _, filenames in os.walk(path)
                 for filename in filenames)
        for path in paths:
            newpath = path.replace(' ', '-')
            newname = newpath.replace(',', '')
            if newname != path:
                os.rename(path, newname)

    def set_num_scapes(self, num):

        """

        Parameters
        ----------
        num:    number of soundscapes to generate

        """

        self.num_scapes = num

    def set_fg_path(self, new_path):
        """

        Parameters
        ----------
        new_path:   path to foreground audio

        """

        self.fpath1 = new_path

    def set_bg_path(self, new_path):
        """

        Parameters
        ----------
        new_path:   path background soundscape audio

        """
        self.fpath2 = new_path


    def set_duration(self, duration):

        """

        Parameters
        ----------
        duration:   duration of output soundscape

        """
        self.duration = duration

    def set_snr(self, snr):
        """

        Parameters
        ----------
        snr:        signal to noise ratio

        """
        self.snr = snr

    def set_class(self, mode, newclass):

        """

        Parameters
        ----------
        newclass:   new class to select
        mode        'foreground' or 'background' to assign class

        """
        if mode == 'foreground':
            self.fg_class = newclass
        elif mode == 'background':
            self.bg_class = newclass

    def set_start_times(self, mode, times):
        if mode == 'foreground':
            self.fg_start = times

        elif mode == 'background':
            self.bg_start = times



    def generate_soundscapes(self, fgs, bgs, outfile, bg_start=None, fg_start=None):

        """

        Parameters
        ----------
        fgs:        foreground files
        bgs:        background files
        outfile:    save soundscape as
        bg_start:   background start times - needed?
        fg_start:   foreground start times

        """
        event_starts = []
        event_ends = []
        event_labels = []
        event_source = []
        event_source_start = []
        event_source_end = []
        event_snr = []
        event_role = []

        events = pd.DataFrame(columns=['start_time', 'end_time', 'label', 'src_file', 'src_start', 'src_end', 'snr', 'role'])

        # determine number of foreground elements to include
        if fg_start ==  None:
            num_events = 1
        elif type(fg_start) == int:
            num_events = 1
        else:
            num_events = len(fg_start)

        # choose background file for this soundscape
        randx = round(random.random() * len(bgs)-1)             # hack..
        curr_bg_file = bgs['file_name'][randx]

        # no background start time provided, chose randomly
        if bg_start == None:

            # duration > file length
            # set duration to length of file, and start to 0 - FIX: should this just use a different bg file?
            if self.duration > sox.file_info.duration(curr_bg_file):
                self.duration = sox.file_info.duration(curr_bg_file)
                bg_start_time = 0
                warnings.warn('Warning, provided duration exceeds length of background file. Duration set to ' +
                              str(sox.file_info.duration(curr_bg_file)))

            # use random start time within range
            else:
                print 'random bg start'
                bg_start_time = random.random() * (sox.file_info.duration(curr_bg_file) - self.duration)

        # background start time provided
        else:
            if type(bg_start) is list:
                # FIX -- this uses random bg files when list is passed
                randx = int(round(random.random()*len(bg_start)-1))
                print '!!!!!!!!!!!!!!!!!!!!!!'
                print randx
                bg_start_time = bg_start[randx]
            elif type(bg_start) is int:
                bg_start_time = bg_start

            if bg_start_time + self.duration > sox.file_info.duration(curr_bg_file):
                # print bg_start
                # print duration
                # print sox.file_info.duration(curr_bg_file)
                bg_start_time = sox.file_info.duration(curr_bg_file) - self.duration
                # if start time is now negative, set it to 0 and use duration as length of file
                if bg_start_time < 0:
                    bg_start_time = 0
                    duration = sox.file_info.duration(curr_bg_file)
                warnings.warn(
                    'Warning, provided start time and duration exceeds length of background file. Start time set to ' +
                    str(bg_start_time) + '. Durration set to ' + str(duration))

        tmp = 10 + len(self.bg_class)
        scape_file = outfile[tmp:-4] + '.wav'
        scape_file_out = outfile + str(0) + '.wav'

        print '\n'
        print 'scape_file: '+scape_file
        print '\n'
        print bg_start_time
        print self.duration

        # create pysox transformer for background
        bg = sox.Transformer(curr_bg_file, scape_file_out)

        # trim background to user selected duration
        bg.trim(bg_start_time, bg_start_time + self.duration)

        # normalize background audio to MAX_DB
        bg.norm(self.MAX_DB)

        # save trimmed and normalized background
        bg.build()

        for n in range(0, num_events):

            # pick bg and fg files -- FIX: currently just picks according to loop
            curr_fg_file = fgs['file_name'][n]

            # no foreground start times provided, chose randomly
            if fg_start == None:
                fg_start_time = round(random.random() * (self.duration - sox.file_info.duration(curr_fg_file)))
            else:
                # choose start times from list provided -- FIX: currently picks according to loop
                if type(fg_start) is list:
                    print 'fg list'
                    fg_start_time = fg_start[n]
                # use single start time provided
                elif type(fg_start) is int:
                    fg_start_time = fg_start

            # keep track of event entries
            event_starts.append(fg_start_time)
            event_ends.append(fg_start_time + sox.file_info.duration(curr_fg_file))
            event_labels.append(self.fg_class)
            event_source.append(curr_fg_file)
            event_source_start.append(0)
            event_source_end.append(sox.file_info.duration(curr_fg_file))
            event_snr.append(self.snr)
            event_role.append('event')

            # output file names for temp storage of normalized files
            tmp = 10 + len(self.fg_class)
            fg_out_file = 'audio/output/' + curr_fg_file[tmp:-4] + '_norm_out.wav'

            # normalize bg to desired dB to ensure SNR
            fg_gain = self.MAX_DB - self.snr

            # normalize fg to desired max dB
            fg = self.normalize_file(curr_fg_file, self.MAX_DB, fg_out_file)

            # pad to foreground start time
            fg.pad(fg_start_time,0)

            # # have to expicitly write these?
            fg.build()

            # combine the foreground and background files
            last_scape_file = outfile+str(n)+'.wav'
            scape_file_out = outfile+str(n+1)+'.wav'
            scape_out = sox.Combiner([fg_out_file, last_scape_file], scape_file_out, 'mix')
            print '-----------'
            print fg_out_file
            print scape_file_out
            print '-----------'
            scape_out.build()

            # MAYBE THIS CAN ALL BE DONE WITH COMBINER?
            # scape2_out = sox.Combiner([curr_fg_file, curr_bg_file], 'audio/output/mixed_just_comb.wav', 'mix',[-3,-13])
            # scape2_out.build()

        # foreground events
        events['start_time'] = event_starts
        events['end_time'] = event_ends
        events['label'] = event_labels
        events['src_file'] = event_source
        events['src_start'] = event_source_start
        events['src_end'] = event_source_end
        events['snr'] = event_snr
        events['role'] = event_role

        # background
        events.loc[len(events)] = [0, self.duration, self.bg_class, curr_bg_file, bg_start_time, bg_start_time + self.duration, 0, 'background']

        # generate jams file
        self.generate_jams(events, 'scape', 'scape.jams')

if __name__ == '__main__':


    sc = Scaper('audio/fg','audio/bg', 'voice', 'music')
    sc.set_class('foreground','voice')
    sc.set_class('background', 'music')

    sc.set_num_scapes(1)
    sc.set_snr(20)
    sc.set_duration(30)
    sc.generate_soundscapes(sc.fgs, sc.bgs, 'audio/output/this_scape.wav', fg_start=[5,10,15])

    # print sc.fgs