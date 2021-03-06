"""
-------------------------- Behold  Artificial Islands -------------------------

contains the calo, template, particle, and island classes for making artificial
pileup islands for the E989 muon g-2 experiment.

Written by Lars Borchert with extensive help from Josh LaBounty

-------------------------------------------------------------------------------
"""
import numpy as np
import fclParse
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.pylab as pylab
import ROOT as r
import json

with open("artificialIslands_config.json") as config_file:
    config = json.load(config_file)

moliere_radius = config['moliereRadius'] / 2.5


def draw(this_island, legend=False, show_moliere_radius=False,
         show_hit_xtals=False, show_xtal_energies=False,
         show_hit_label=False, show_traces=False, energy_cmap=False,
         ring_alpha=None, label_e_scale='G'):
    """
    Give a matplotlib representation of this calorimeter

    ------------- Parameters -------------
    """
    fig, ax = plt.subplots(1, 1)
    fig.set_size_inches(9, 6)

    for x in range(1, 9):
        ax.axvline(x=x, ymin=0, ymax=6, color='xkcd:grey')

    for y in range(1, 6):
        ax.axhline(y=y, xmin=0, xmax=9, color='xkcd:grey')

    # every bin is 10 MeV
    colors = pylab.cm.viridis(np.linspace(0, 1, 100))

    if (not ring_alpha):
        if (show_traces):
            ring_alpha = 0.3
        else:
            ring_alpha = 1

    impact_num = 1
    for impact in this_island.calo.impacts:

        if (energy_cmap):
            color_index = impact["energy"] // 40
            if (color_index >= 100):
                color_index = 99
            this_color = colors[color_index]
        else:
            this_color = next(ax._get_lines.prop_cycler)['color']

        if (label_e_scale == 'M'):
            this_label = "P{0}  ".format(impact_num) + \
                            "{0:.0f} MeV ".format(impact["energy"]) + \
                            "{0:.2f} ns".format(impact['time'])
        else:
            this_label = "P{0}  ".format(impact_num) + \
                            "{0:.2f} GeV ".format(impact["energy"]/1000) + \
                            "{0:.2f} ns".format(impact['time'])

        ax.plot(impact["x"], impact["y"],
                marker='o', markersize=10, color=this_color,
                alpha=ring_alpha,
                label=this_label)

        if (show_hit_label):
            ax.text(x=impact["x"]+0.15, y=impact["y"]-0.2,
                    s="P"+str(impact_num), color=this_color, size=18,
                    alpha=ring_alpha)

        # ax.plot(impact["ring_x"], impact["ring_y"], color=this_color)
        # ax.plot(impact["small_ring_x"], impact["small_ring_y"],
        #        color=this_color)

        moliere_circle = plt.Circle((impact["x"], impact["y"]),
                                    moliere_radius, color=this_color,
                                    linewidth=3, fill=False,
                                    alpha=ring_alpha)
        moliere_circle_2 = plt.Circle((impact["x"], impact["y"]),
                                      2*moliere_radius,
                                      color=this_color,
                                      linewidth=3, fill=False,
                                      alpha=ring_alpha)

        if (show_hit_xtals):
            for hit_crystal in impact["hit_crystals"]:
                rect = patches.Rectangle((hit_crystal[0], hit_crystal[1]),
                                         1, 1, linewidth=3,
                                         edgecolor='none',
                                         facecolor='xkcd:light grey')
                ax.add_patch(rect)

        if (show_xtal_energies):
            for xtal in impact["hit_crystals"]:
                xtal_events = this_island.calo.xtalGrid[xtal[0]
                                                        ][xtal[1]].impacts
                energies_list = []
                for event in xtal_events:
                    energies_list.append(event[1])
                energy_string = ""
                for val in energies_list:
                    energy_string += "{0} MeV \n".format(int(val))
                ax.text(x=xtal[0]+0.1, y=xtal[1],
                        s=energy_string)

        if (show_moliere_radius):
            ax.add_artist(moliere_circle)
            ax.add_artist(moliere_circle_2)

        impact_num += 1

    if (show_traces):
        # loop over columns
        for i in range(0, len(this_island.calo.xtalGrid)):
            # loop over rows
            for j in range(0, len(this_island.calo.xtalGrid[i])):
                if (this_island.calo.xtalGrid[i][j].trace is not []):
                    axin = ax.inset_axes([i/9, j/6, 1/9, 1/6])
                    axin.plot(this_island.calo.xtalGrid[i][j].choppedTrace)
                    axin.get_xaxis().set_ticks([])
                    axin.get_yaxis().set_ticks([])
                    axin.patch.set_alpha(0)

                    # we need to make sure they are put on the same
                    # scale
                    if (config['normalizeXtal']):
                        axin.set_ylim(-0.1, 0.8)
                    else:
                        axin.set_ylim(config['pedestal'] - 200,
                                      config['pedestal'] + 2500)

    ax.set_xlim(0, 9)
    ax.set_ylim(0, 6)
    if (legend):
        ax.legend()
    # return fig


class Template:
    """
    Take a root spline and make a simple,
    pythonified object with two np arrays.

    ------------ Attributes ------------

    splineY      : [ndarray] the y values in the spline. They are
                   normalized such that their integral in time
                   is equal to one

    time         : [ndarray] the x values in the spline, which are time

    samplingRate : [float] the sampling rate of the undigitized spline

    xtalNum      : [int] the crystal number of the template
    """
# -----------------------------------------------------------------------------
# ----------------------------- Public  Functions -----------------------------
# -----------------------------------------------------------------------------

    def peakTime(self):
        """
        Gives the time when a peak occurs
        """
        index = np.argmax(self.trace)
        # print(index)
        return(self.time[index])

    def getPeak(self):
        """
        Gives the value of the peak of the spline
        """
        return np.max(self.trace)

    def getNormalIntegral(self):
        """
        Gives the pulse integral of the peak-normalized spline
        Essentially a unit pulse integral. "Peak-normalized" in
        this case means that the peak of the spline is equal
        to one, rather than the integral of the spline equal to one
        """
        scaledVals = self.trace / self.getPeak()
        return np.sum(scaledVals) * self.samplingRate

# -----------------------------------------------------------------------------
# ----------------------------- Private Functions -----------------------------
# -----------------------------------------------------------------------------

    def __init__(self, pySpline=None,
                 rSpline=None, xtalNum=None, caloNum=None):
        """
        rSpline : a ROOT spline, representing a normalized pulse
                  template

        xtalNum : [int] the crystal number this spline is based from

        caloNum : [int] the calo number this spline is based from
        """

        trace = []
        times = []

        for i in np.linspace(rSpline.GetXmin(),
                             rSpline.GetXmax(),
                             rSpline.GetNpx()):
            trace.append(rSpline.Eval(i))
            times.append(i)

        self.trace = trace
        self.time = times

        self.samplingRate = times[2] - times[1]

        self.xtalNum = xtalNum
        self.caloNum = caloNum


class Xtal:
    """

    ------------ Attributes ------------

    caloNum : [int] the number of the calorimeter where this crystal lives

    x       : [int] the x position of this crystal, in crystal units

    y       : [int] the y position of this crystal, in crystal units

    eCalVal : [float] the energy calibration value for this crystal

    trace   :

    times   :

    impacts :
    """
# -----------------------------------------------------------------------------
# ----------------------------- Public  Functions -----------------------------
# -----------------------------------------------------------------------------
    def energize(self, impact_time, xtal_energy):
        """
        Put energy into this crystal. The energy is calculated at the
        calorimeter level
        """
        self.impacts.append([impact_time, xtal_energy])

    def build_trace(self):
        """
        Finalizes the crystal, gets the trace set up. In version one this
        was done in the constructor, but we need to be able to add energy
        values to this crystal before building it.
        """

        """randomize the length of the tail samples"""

        if(config['randomizeTailLength']):
            self.nTailSamples = self.giveRandomTailLength_()

        # before putting pulses in, trace values are just zero
        thisTrace = np.append(np.zeros_like(self.template.trace),
                              np.zeros(self.nTailSamples))

        """setup the template variables"""

        templateTimes = self.template.time
        templateSamplingRate = self.template.samplingRate

        """define the trace and time arrays"""

        # the time array is the original one, plus however much else we want
        # based on nTailSamples
        theseTimes = np.append(templateTimes,
                               np.array([templateTimes[len(templateTimes)-1] +
                                         templateSamplingRate*i
                                         for i in range(1,
                                                        self.nTailSamples+1)]))

        """Now we can put the pulses together"""

        templateShape = self.template.trace / self.template.getPeak()
        # templatePeakTime = self.template.peakTime()
        # print(templatePeakTime)
        emptyTrace = thisTrace.copy()

        pulses = []
        for event in self.impacts:
            deltaT = event[0] / 2
            energy = event[1]
            height = self.convertToADC_(energy)

            sample_offset = int(deltaT)  # / self.template.samplingRate)
            # print(sample_offset)
            splineI = np.interp(templateTimes + deltaT - sample_offset,
                                templateTimes, templateShape) * height

            thisTrace[sample_offset:sample_offset + len(splineI)] += splineI

            thisPulse = emptyTrace.copy()
            thisPulse[sample_offset:sample_offset + len(splineI)] += splineI
            pulses.append(thisPulse)

        """get the sampling right"""

        thisTrace, theseTimes = self.digitize_(self.verbosity,
                                               thisTrace,
                                               theseTimes)

        for pulse in pulses:
            emptyTimes = theseTimes.copy()[:len(pulse)]
            thisPulse, someTimes = self.digitize_(False, pulse, emptyTimes)

        """add gaussian noise to each sample"""

        if (config['noise']):
            thisTrace = self.giveNoise_(thisTrace)

        """compute this islands integral"""

        self.integral = self.integrate_(theseTimes, thisTrace)

        """normalize if needed"""

        if (config['normalizeXtal']):
            # if we are normalizing, our chopping threshold needs to match
            # our normalization
            thisTrace /= self.integral
            self.chopThreshold /= self.integral
        elif (config['doPedestal']):
            # if we don't want to normalize, we should make it look like it
            # came from an ADC, with a pedestal
            thisTrace = self.addPedestal_(thisTrace)

        """now we're done!"""
        self.time = theseTimes
        self.trace = thisTrace.tolist()

    def do_chop(self, startIndex, endIndex):
        """
        Performs chopping with the indices found at the calo level
        """
        # first, we need to make sure that the end index is smaller than the
        # length of the trace to avoid out of bounds errors. Within an island,
        # it is important that each trace is the same length. Padding happens
        # at the dataset level later.
        if (self.trace):
            if (endIndex > len(self.trace)):
                self.choppedTrace = self.trace[startIndex:]
                self.choppedTrace.append(
                    np.zeros(endIndex-len(self.trace)).tolist())
            else:
                self.choppedTrace = self.trace[startIndex:endIndex]
        else:
            self.choppedTrace = []

    def find_chop_indices(self):
        """
        goes through the trace and gives chop index recommendation based on
        this crystal and the config thresholds
        """
        startIndex = None
        endIndex = None

        # loop through all the values
        for index, val in enumerate(self.trace):
            if (val > self.chopThreshold):
                # for something over our threshold, make an endIndex
                endIndex = index + config['nPostSamples']

                # make sure we don't get out of bounds errors
                # if we are already at the end of the trace, we can end here
                if (endIndex >= len(self.trace)):
                    endIndex = len(self.trace)
                    break

                # if this is the first threshold passer, get the startIndex
                if (startIndex is None):
                    if(index - config['nPreSamples'] > 0):
                        startIndex = index - config['nPreSamples']
                    else:
                        startIndex = 0

        return startIndex, endIndex

# -----------------------------------------------------------------------------
# ----------------------------- Private Functions -----------------------------
# -----------------------------------------------------------------------------

    def digitize_(self, verbosity, thisTrace, theseTimes):
        """
        convert the time sampling to match that of the ADC
        by default this should be 1.25ns sampling
        """
        if (config['samplingRateArtificial'] is None):
            return thisTrace, theseTimes

        assert type(config['samplingRateArtificial']) is float, print(
            """Error: Sampling rate must be a float.
            Currently {0}""".format(type(config['samplingRateArtificial']))
        )

        if (verbosity):
            print("Sampling this trace with a deltaT of " +
                  "{0:.2f} ns".format(config['samplingRateArtificial']))

        sampledTimes = [theseTimes[0]]

        while(sampledTimes[-1] < [theseTimes[-1]]):
            sampledTimes.append(sampledTimes[-1] +
                                config['samplingRateArtificial'])

        theseSamples = np.interp(sampledTimes, theseTimes, thisTrace)

        thisTrace = theseSamples
        theseTimes = sampledTimes

        return thisTrace, theseTimes

    def giveRandomTailLength_(self):
        """
        figure out how long the tail will be
        never run this outside of initialization
        """
        nTailSamples = self.nTailSamples + np.random.randint(-50, 100)
        if(self.verbosity):
            print(nTailSamples, " tail samples in this island")
        return nTailSamples

    def convertToADC_(self, energy):
        """
        convert some energy to ADC units for this crystal
        """
        normalIntegral = self.template.getNormalIntegral()
        thisHeight = energy / (self.energyCalibrationVal * normalIntegral *
                               self.template.getPeak())
        return thisHeight

    def giveNoise_(self, thisTrace):
        """
        adds gaussian noise into the island, in ADC units. Do not use this
        function unless you are operating in ADC units
        """
        thisTrace += np.random.normal(0, self.noiseLevel, size=thisTrace.size)

        if (self.verbosity):
            print("The noise level standard deviation in this trace: " +
                  "{0:.2f}".format(self.noiseLevel))

        return thisTrace

    def clear_(self):
        """
        Deletes information from this crystal
        """
        self.impacts = []
        self.trace = []
        self.time = []

    def addPedestal_(self, trace):
        """
        This just shifts all the trace by the pedestal
        value, to make the y axis scale a little more realistic. For
        right now, the pedestal value is just made randomly. As far as
        I know there is no fcl file with the pedestal values for each
        crystal, but if there are that would be better.
        """

        self.pedestal = np.random.normal(loc=1750, scale=2.5) * (-1)
        # correct the chopThreshold too
        self.chopThreshold += self.pedestal

        if(config['verbosity']):
            print("The pedestal value of this crystal is " +
                  "{0:.2f}".format(self.pedestal))

        return (trace + self.pedestal)

    def integrate_(self, time, trace):
        """
        Returns the integral of the trace, the area under the curve
        """
        return (np.sum(trace) * (time[1]-time[0]))

    def __init__(self,
                 caloNum=None,
                 x=None,
                 y=None,
                 xtalNum=None):
        """
        caloNum : [int] the number of the calorimeter where this crystal lives

        x       : [int] the x position of this crystal, in crystal units

        y       : [int] the y position of this crystal, in crystal units

        eCalVal : [float] the energy calibration value for this crystal
        """
        self.caloNum = caloNum
        self.x = x
        self.y = y
        self.xtalNum = xtalNum
        self.impacts = []
        self.noise = config['noise']
        self.nTailSamples = config['nTailSamples']
        self.samplingRateArtificial = config['samplingRateArtificial']
        self.pedestal = config['pedestal']
        self.verbosity = config['verbosity']

        self.time = []
        self.trace = []

        self.integral = None

        self.noiseLevel = \
            fclParse.fclReader(config['noiseValueFcl'])[
                               'pedestalConstantsLaserRun3'][
                               'calo'+str(caloNum)]['xtal' + str(xtalNum)][
                               'noiseLevel']

        self.energyCalibrationVal = \
            fclParse.fclReader(config['energyCalibrationFcl'])[
                               'absolute_calibration_constants'][
                               'calo'+str(caloNum)]['xtal'+str(xtalNum)]

        f = r.TFile(config['templateFile'])
        self.template = Template(rSpline=f.Get("masterSpline_xtal" +
                                               str(self.xtalNum)),
                                 xtalNum=self.xtalNum, caloNum=self.caloNum)

        self.chopThreshold = self.convertToADC_(config['chopThreshold'])

        def __repr__(self):
            summary = "----- Crystal {0} ----\n-".format(self.xtalNum)
            summary += "Location : ({0}, {1})\n".format(self.x, self.y)
            summary += "Impacts :\n"
            for i in self.impacts:
                summary += "   Energy : {0:.2f} MeV".format(i[1]) + \
                           "   Time : {0:.2f}\n".format(i[0])
            if (self.noise):
                summary += "Noise Level : {0}\n".format(self.noiseLevel)
            else:
                summary += "This crystal is noiseless\n"

            return summary


class Calorimeter:
    """
    Where the magic happens. Essentially just a 6x9 matrix of crystal objects.
    Each of those has a spline or none at some time, which is what goes into an
    island object. We probably don't need Calo and Island to be separate, but
    it makes it a litte easier for me to think about, and makes expansion easy

    ------------ Attributes ------------

    caloNum  : [int] the number of this calorimeter, 1 to 24

    xtalGrid : [2D list] a list of crystal objects

    """
# -----------------------------------------------------------------------------
# ----------------------------- Public  Functions -----------------------------
# -----------------------------------------------------------------------------
    def impact(self, p):
        """
        A positron hits. Send time and energy information to the crystals,
        making sure to send the correct energy to each crystal. Energies are
        determined by overlapping an area onto the calorimeter face. In this
        area, there is an energy density with some sort of falloff. The total
        energy is the energy passed to this function. Integrate the energy
        density over the area overlapping this energy impact area with each
        crystal, and tell that crystal that it got a signal with that energy at
        this time
        """
        impact_radius = 2 * moliere_radius
        self.impacts.append({"x": p.x,
                             "y": p.y,
                             "time": p.time,
                             "energy": p.energy,
                             "ring_x": impact_radius
                             * np.cos(np.linspace(0, 2 * np.pi, 17))
                             + p.x,
                             "ring_y": impact_radius
                             * np.sin(np.linspace(0, 2 * np.pi, 17))
                             + p.y,
                             "small_ring_x": moliere_radius
                             * np.cos(np.linspace(0, 2 * np.pi, 17))
                             + p.x,
                             "small_ring_y": moliere_radius
                             * np.sin(np.linspace(0, 2 * np.pi, 17))
                             + p.y})

    def clear(self):
        """
        Deletes all the impacts, clears the crystal grid
        """
        self.impacts = []
        self.reset_xtalGrid_()

    def chop(self):
        """
        Performs simulated island chopping. We don't want a bunch of zero
        values if we have many many data, so we cut islands
        down to just the interesting stuff. We keep preSamples before the
        first value over our threshold value, and postSamples after the
        last
        """
        # we need to go through each crystal, find a start and end index.
        # then we need to go through each index, find the extrema
        # then we need to go back to each crystal, and use these indices
        # to chop each crystal's trace to the same length
        startIndices = []
        endIndices = []

        for column in self.xtalGrid:
            for xtal in column:
                this_start, this_end = xtal.find_chop_indices()
                if ((this_start is None) or (this_end is None)):
                    continue
                startIndices.append(this_start)
                endIndices.append(this_end)

        # print(startIndices, endIndices)
        the_start = min(startIndices)
        # print(the_start)
        the_end = max(endIndices)
        # print(the_end)

        self.chop_size = the_end - the_start

        for column in self.xtalGrid:
            for xtal in column:
                xtal.do_chop(the_start, the_end)

    def build(self):
        """
        after things have impacted, we build all the traces
        """
        self.get_hit_crystals_()
        self.build_impacted_crystals_()

# -----------------------------------------------------------------------------
# ----------------------------- Private Functions -----------------------------
# -----------------------------------------------------------------------------

    def get_energy_density_(self, r):
        """
        The energy density of the impacted particle over the region of impact.
        This will change, 1/r is definitely not right but easy for testing
        """
        return 1 / (2 + 2 * np.pi * r**2)

    def get_crystal_energy_(self, xtal_loc, impact_loc, impact_energy):
        """
        For some crystal, hit location, and hit energy, we calculate how much
        energy was deposited into this crystal.

        Currently this method is inaccurate. We are assuming that the energy
        is distributed evenly accross the face of the crystal, with the energy
        density of the center of the crystal. Additional complications come
        from energy loss at the borders of crystals. These are ignored. We can
        do this for now because we are mostly interested in the number of
        impacts, not the specific energies.
        """
        imp_x = impact_loc[0]
        imp_y = impact_loc[1]
        xtal_x = xtal_loc[0] + 0.5
        xtal_y = xtal_loc[1] + 0.5
        r = np.sqrt(((xtal_x - imp_x)**2) + ((xtal_y - imp_y)**2))
        e_density = self.get_energy_density_(r)

        # crystal has area of 1
        return e_density * impact_energy

    def get_hit_crystals_(self):
        """
        """
        # first, let's just flag where the moliere circle overlaps crystals
        # not all of these crystals will end up mattering, as it is likely
        # that the edge ones will get less than 50 MeV

        # loop through the impacts
        for impact in self.impacts:
            impact["hit_crystals"] = []
            impact_loc = (impact['x'], impact['y'])
            this_x = int(impact['x'])
            this_y = int(impact['y'])
            if ((this_x >= 9) or (this_y >= 6)):
                continue

            # first check the center of the impact. This is important because
            # without checking here, an impact directly centered on one crystal
            # can get skipped by just checking the rings
            if ((this_x, this_y) not in impact["hit_crystals"]):
                impact["hit_crystals"].append((this_x, this_y))
                xtal_energy = self.get_crystal_energy_((this_x, this_y),
                                                       impact_loc,
                                                       impact['energy'])
                self.xtalGrid[this_x][this_y].energize(impact['time'],
                                                       xtal_energy)

            # loop for the 2nd Moliere radius
            for i in range(0, len(impact["ring_x"])):
                # for this location on the Moliere ring, take note of the
                # crystal coordinate
                this_x = int(impact["ring_x"][i])
                this_y = int(impact["ring_y"][i])
                # check that this crystal actually exists on the calo face
                if ((this_x >= 9) or (this_y >= 6)
                   or (this_x < 0) or (this_y < 0)):
                    continue
                # check the crystal has not already been counted, count it
                if ((this_x, this_y) not in impact["hit_crystals"]):
                    impact["hit_crystals"].append((this_x, this_y))
                    xtal_energy = self.get_crystal_energy_((this_x, this_y),
                                                           impact_loc,
                                                           impact['energy'])
                    self.xtalGrid[this_x][this_y].energize(impact['time'],
                                                           xtal_energy)

            # loop for the 1st Moliere radius
            for i in range(0, len(impact["small_ring_x"])):
                # for this location on the Moliere ring, take note of the
                # crystal coordinate
                this_x = int(impact["small_ring_x"][i])
                this_y = int(impact["small_ring_y"][i])
                # check that this crystal actually exists on the calo face
                if ((this_x >= 9) or (this_y >= 6)
                   or (this_x < 0) or (this_y < 0)):
                    continue
                # check the crystal has not already been counted, count it
                if ((this_x, this_y) not in impact["hit_crystals"]):
                    impact["hit_crystals"].append((this_x, this_y))
                    xtal_energy = self.get_crystal_energy_((this_x, this_y),
                                                           impact_loc,
                                                           impact['energy'])
                    self.xtalGrid[this_x][this_y].energize(impact['time'],
                                                           xtal_energy)

    def build_impacted_crystals_(self):
        """
        Go through the xtalGrid, and build any non empty crystals' traces
        """
        for column in self.xtalGrid:
            for xtal in column:
                # check that the crystal has been hit
                if xtal.impacts:
                    if (config['verbosity']):
                        print("building trace for xtal " +
                              "{0}".format(xtal.xtalNum))
                    # check that the crystal got energy above a threshhold
                    energy_check = False
                    for impact in xtal.impacts:
                        if (impact[1] >= config['minFitEnergy']):
                            energy_check = True
                    if (energy_check):
                        xtal.build_trace()

    def reset_xtalGrid_(self):
        """
        Creates a fresh grid of crystals. Use when initializing the calo, or
        when clearing it of impacts.
        """
        xtalGrid = []
        for column in range(0, 9):
            this_column = []
            for row in range(0, 6):
                this_num = (row * 9) + (column)
                this_xtal = Xtal(caloNum=self.caloNum,
                                 x=column+1,
                                 y=row+1,
                                 xtalNum=this_num)

                this_column.append(this_xtal)
            xtalGrid.append(this_column)
        self.xtalGrid = xtalGrid

    def __init__(self, caloNum):
        """
        """
        self.caloNum = caloNum
        self.impacts = []
        # self.impacts_registered_by_xtals = []

        # create our grid
        self.reset_xtalGrid_()

    def __repr__(self):
        summary = ""

        for columm in self.xtalGrid:
            for xtal in columm:
                this_report = "Crystal {0} at {1} has \
[time (ns), energy (MeV)]: {2}".format(xtal.xtalNum,
                                       (xtal.x, xtal.y),
                                       xtal.impacts)
                summary += this_report + "\n\n"

        return summary


class Island:
    """

    ------------ Attributes ------------

    """
# -----------------------------------------------------------------------------
# ----------------------------- Private Functions -----------------------------
# -----------------------------------------------------------------------------

    def giveNPulses_(self, verbosity, minPulses, maxPulses):
        """
        figure out how many pulses there will be
        never run this outside of initialization
        """
        nPulses = np.random.randint(minPulses, maxPulses+1)
        if(verbosity):
            print("The number of pulses in this island: " +
                  "{0}".format(nPulses))
        return nPulses

    def giveTimeOffsets_(self, verbosity, deltaTmin, deltaTmax):
        """
        Creates the time offset values for each pulse.
        Make deltaTmax >> minTimeOffset, otherwise
        this will take absolutely forever to run
        """

        check = 0
        # keep looking until every combination of offsets has passed the check
        while(check < self.nParticles ** 2):
            # make some random time offsets
            offsets = np.random.uniform(deltaTmin, deltaTmax,
                                        size=self.nParticles)
            # now we need to make sure they have the right separation
            for i in range(0, len(offsets)):
                for j in range(0, len(offsets)):
                    # a value can be within minTimeOffset of itself of course
                    if(i != j):
                        # if the separation isn't right, reset check
                        # otherwise we are ok, and can increment the number
                        # of correct pairs
                        separation = offsets[i] - offsets[j]
                        if(abs(separation) < self.minTimeOffset):
                            check = 0
                        else:
                            check += 1
                    else:
                        check += 1

        if(verbosity):
            thisString = "["
            for offset in offsets:
                thisString += " {0:.2f} ".format(offset)
            thisString += '] ns'
            print("The time offsets are: " + thisString)
            print("The artificial minimum time offset is: " +
                  "{0:.2f} ns".format(self.minTimeOffset))
        return offsets

    def __init__(self, caloNum=1):
        """
        caloNum:    [int] The calorimeter number of this island
        """

        # decide on particle number
        self.nParticles = self.giveNPulses_(config['verbosity'],
                                            config['minPulses'],
                                            config['maxPulses'])

        # get particle times
        self.minTimeOffset = config['minTimeOffset']
        self.timeOffsets = self.giveTimeOffsets_(config['verbosity'],
                                                 config['deltaTmin'],
                                                 config['deltaTmax'])

        # build particles
        self.particles = []
        for this_time in self.timeOffsets:
            this_particle = Particle(time=this_time)
            self.particles.append(this_particle)

        # make a calorimeter
        self.calo = Calorimeter(caloNum)

        # particles impact the calorimeter
        self.energies_list = []
        for particle in self.particles:
            self.calo.impact(particle)
            self.energies_list.append(particle.energy)

        # give impacted crystals their traces
        self.calo.build()

        if (config['doChop']):
            self.calo.chop()

        # extract traces to output format
        island_trace = []
        for c_index in range(0, len(self.calo.xtalGrid)):
            island_trace.append([])

            for r_index in range(0, len(self.calo.xtalGrid[c_index])):
                if(config['doChop']):
                    this_ct = self.calo.xtalGrid[c_index][
                        r_index].choppedTrace
                    if (not this_ct):
                        this_ct = np.zeros(self.calo.chop_size).tolist()
                    island_trace[c_index].append(this_ct)
                else:
                    island_trace[c_index].append(
                        self.calo.xtalGrid[c_index][r_index].trace)

        island_trace = np.array(island_trace)
        self.saved_traces = np.reshape(island_trace,
                                       (9, 6, self.calo.chop_size))

        self.output = {}
        self.output['trace'] = self.saved_traces
        self.output['nParticles'] = self.nParticles
        self.output['energies'] = self.energies_list

    def __repr__(self):
        summary = "----- New Island -----\n"
        summary += "Number of Particle Hits : {0}\n".format(self.nParticles)
        summary += "Particle Energies : "
        for energy in self.energies_list:
            summary += "{0} MeV    ".format(energy)
        return summary


class Particle:
    """
    Represents a particle that hits the calorimeter, and information
    relevant to that event.

    ------------ Attributes ------------
    x      : [float] the x position of the particle on the calo face, in calo
             crystal units

    y      : [float] the y position of the particle on the calo face, in calo
             crystal units

    energy : [float] the energy of this particle

    time   : [float] the time this particle hits the calorimeter
    """
# -----------------------------------------------------------------------------
# ----------------------------- Private Functions -----------------------------
# -----------------------------------------------------------------------------

    def giveEnergy_(self):
        """
        Calculates and assigns an impact total energy in MeV
        """
        if (config['energyMethod'] == "linear"):
            self.energy = np.random.randint(low=config['eLow'],
                                            high=config['eHigh'])
        else:
            self.energy = None

    def giveX_(self):
        """
        Caclulates and assigns an impact x position
        """
        if (config['positionMethod'] == "random"):
            self.x = np.random.uniform(low=0.0, high=9.0)
        else:
            self.x = None

    def giveY_(self):
        """
        Calculates and assigns an impact y position
        """
        if (config['positionMethod'] == "random"):
            self.y = np.random.uniform(low=0.0, high=6.0)
        else:
            self.y = None

    def __init__(self, time=None, x=None, y=None, energy=None):
        """
        x      : [float] the x position of the particle on the calo face,
                 in calo crystal units

        y      : [float] the y position of the particle on the calo face,
                 in calo crystal units

        energy : [float] the energy of this particle

        time   : [float] the time this particle hits the calorimeter
        """
        if (x is None):
            self.giveX_()
        else:
            self.x = x

        if (y is None):
            self.giveY_()
        else:
            self.y = y

        if (energy is None):
            self.giveEnergy_()
        else:
            self.energy = energy

        if (time is None):
            self.time = np.random.uniform(low=config['deltaTmin'],
                                          high=config['deltaTmax'])
        else:
            self.time = time

    def __repr__(self):
        summary = "\n----- New Particle -----\n"

        summary += "(x, y) : ({0:.2f}, {1:.2f})\n".format(self.x, self.y)
        summary += "Energy : {0:.2f} MeV\n".format(self.energy)
        summary += "Time : {0:.2f} ns\n".format(self.time)

        return summary
