// FLIM.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#pragma warning(disable : 4996)

#include <iostream>
#include <chrono>
#include <thread>
#include <windows.h>
#include <dos.h>
#include <stdio.h>
#include <conio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#include <sstream>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
extern "C"
{
#include <errorcodes.h>
#include <th260defin.h>
#include <th260lib.h>
#include <Thorlabs.MotionControl.KCube.Piezo.h>
}

using namespace std;
using std::to_string;

unsigned int counts[MAXINPCHAN][MAXHISTLEN]; //array to store data
int Tacq = 5000; //Measurement time in millisec, you can change this
int errorCount = 0;

int dev[MAXDEVNUM];
int found = 0;
FILE* fpout;
int retcode;
int ctcstatus;
char LIB_Version[8];
char HW_Model[16];
char HW_Partno[8];
char HW_Version[16];
char HW_Serial[8];
char Errorstring[40];
int NumChannels;
int HistLen;
int Binning = 3; // 0 => bin width of 0.025 ns, 1 => bin width of 0.05 ns, 2 => bin width of 0.1 ns, 3 => bin width of 0.2 ns
int Offset = 0;
int SyncOffset = 25000;
//int Tacq = 5000; //Measurement time in millisec, you can change this
int SyncDivider = 1; //you can change this

//These settings will apply for TimeHarp 260 P boards
int SyncCFDZeroCross = -10; //you can change this
int SyncCFDLevel = -100; //you can change this
int InputCFDZeroCross = -10; //you can change this
int InputCFDLevel = -30; //you can change this (-30 for monochromator/pmt, -100 for SPAD)

//These settings will apply for TimeHarp 260 N boards
int SyncTiggerEdge = 0; //you can change this
int SyncTriggerLevel = -50; //you can change this
int InputTriggerEdge = 0; //you can change this......
int InputTriggerLevel = -50; //you can change this

double Resolution;
int Syncrate;
int Countrate;
double Integralcount;
int i, j;
int flags;
int warnings;
char warningstext[16384]; //must have 16384 bytest text buffer
char cmd = 0;
string StageCode = "null";
float wl = 800;

bool CreateFullDirectory(const std::string& path) {
    std::string partial;
    std::istringstream ss(path);
    std::string token;

    // Split path by slash
    while (std::getline(ss, token, '/')) {
        if (!token.empty()) {
            partial += token + '/';
            CreateDirectoryA(partial.c_str(), NULL);
        }
    }

    // Check if final directory exists or created
    DWORD attribs = GetFileAttributesA(path.c_str());
    return (attribs != INVALID_FILE_ATTRIBUTES && (attribs & FILE_ATTRIBUTE_DIRECTORY));
}

unsigned int* ex(string outputDir, int xPos, int yPos);
unsigned int* Initialize(string outputDir, int xPos, int yPos);
unsigned int* measure(string outputDir, int xPos, int yPos);

//Initializes tcspc board
unsigned int* Initialize(string outputDir, int xPos, int yPos) {
    StageCode = "Initialize";
    for (i = 0; i < MAXDEVNUM; i++)
    {
        retcode = TH260_OpenDevice(i, HW_Serial);
        if (retcode == 0) //Grab any device we can open
        {
            //printf("\n  %d        %7s    open ok", i, HW_Serial);
            dev[found] = i; //keep index to devices we want to use
            found++;
        }
        else
        {
            
        }
    }

    //In this demo we will use the first device we find, i.e. dev[0].
    //You can also use multiple devices in parallel.
    //You can also check for specific serial numbers, so that you always know 
    //which physical device you are talking to.

    if (found < 1)
    {
        printf("\nNo device available.");
        ex(outputDir, xPos, yPos);
    }
    //printf("\nUsing device #%d", dev[0]);

    //printf("\nInitializing the device...");

    retcode = TH260_Initialize(dev[0], MODE_HIST);  //Histo mode with internal clock
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        //printf("\nTH260_Initialize error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    retcode = TH260_GetHardwareInfo(dev[0], HW_Model, HW_Partno, HW_Version);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        //printf("\nTH260_GetHardwareInfo error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }
    else
        //printf("\nFound Model %s Part no %s Version %s", HW_Model, HW_Partno, HW_Version);


    retcode = TH260_GetNumOfInputChannels(dev[0], &NumChannels);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_GetNumOfInputChannels error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }
    else
        //printf("\nDevice has %i input channels.", NumChannels);


    retcode = TH260_SetSyncDiv(dev[0], SyncDivider);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nPH_SetSyncDiv error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    if (strcmp(HW_Model, "TimeHarp 260 P") == 0)  //Picosecond resolving board
    {
        retcode = TH260_SetSyncCFD(dev[0], SyncCFDLevel, SyncCFDZeroCross);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_SetSyncCFD error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        for (i = 0; i < NumChannels; i++) // we use the same input settings for all channels
        {
            retcode = TH260_SetInputCFD(dev[0], i, InputCFDLevel, InputCFDZeroCross);
            if (retcode < 0)
            {
                TH260_GetErrorString(Errorstring, retcode);
                printf("\nTH260_SetInputCFD error %d (%s). Aborted.\n", retcode, Errorstring);
                ex(outputDir, xPos, yPos);
            }
        }
    }

    if (strcmp(HW_Model, "TimeHarp 260 N") == 0)  //Nanosecond resolving board
    {
        retcode = TH260_SetSyncEdgeTrg(dev[0], SyncTriggerLevel, SyncTiggerEdge);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_SetSyncEdgeTrg error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        for (i = 0; i < NumChannels; i++) // we use the same input settings for all channels
        {
            retcode = TH260_SetInputEdgeTrg(dev[0], i, InputTriggerLevel, InputTriggerEdge);
            if (retcode < 0)
            {
                TH260_GetErrorString(Errorstring, retcode);
                printf("\nTH260_SetInputEdgeTrg error %d (%s). Aborted.\n", retcode, Errorstring);
                ex(outputDir, xPos, yPos);
            }
        }
    }

    retcode = TH260_SetSyncChannelOffset(dev[0], SyncOffset);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_SetSyncChannelOffset error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    for (i = 0; i < NumChannels; i++) // we use the same input offset for all channels
    {
        retcode = TH260_SetInputChannelOffset(dev[0], i, 0);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_SetInputChannelOffset error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }
    }

    retcode = TH260_SetHistoLen(dev[0], MAXLENCODE, &HistLen);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_SetHistoLen error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }
    //printf("\nHistogram length is %d", HistLen);

    retcode = TH260_SetBinning(dev[0], Binning);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_SetBinning error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    retcode = TH260_SetOffset(dev[0], Offset);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_SetOffset error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    retcode = TH260_GetResolution(dev[0], &Resolution);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_GetResolution error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    //printf("\nResolution is %1.0lfps\n", Resolution);

    // After Init allow 150 ms for valid  count rate readings
    // Subsequently you get new values after every 100ms
    //Sleep(150);
    return(0);
}

// measures TCSPC Data
unsigned int* measure(string outputDir, int xPos, int yPos) {

    std::string Directory = "C:/Users/Seyed Sadeghi/Desktop/SpectralFLIM/" + outputDir + "/" + std::to_string(wl);
    if (CreateFullDirectory(Directory)) {
        //printf("worked\n");
    }
    else {
        //printf("didn't work\n");
    }
    string PositionFileName = "C:/Users/Seyed Sadeghi/Desktop/SpectralFLIM/" + outputDir + "/" + std::to_string(wl) + "/" + "x" + std::to_string(xPos) + "_y" + std::to_string(yPos) + ".txt";
    const char* PosFileNamePointer = PositionFileName.c_str();
 
    if ((fpout = fopen(PosFileNamePointer, "w")) == NULL)
    {
        printf("\ncannot open output file\n");
        exit;
    }

    StageCode = "measure";
    retcode = TH260_GetSyncRate(dev[0], &Syncrate);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_GetSyncRate error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }
    //printf("\nSyncrate=%1d/s", Syncrate);


    for (i = 0; i < NumChannels; i++) // for all channels
    {
        retcode = TH260_GetCountRate(dev[0], i, &Countrate);
        if (retcode < 0)
        {
            //TH260_GetErrorString(Errorstring, retcode);
            //printf("\nTH260_GetCountRate error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }
        //printf("\nCountrate[%1d]=%1d/s", i, Countrate);
    }

    //printf("\n");

    //after getting the count rates you can check for warnings
    retcode = TH260_GetWarnings(dev[0], &warnings);
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_GetWarnings error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }
    if (warnings)
    {
        TH260_GetWarningsText(dev[0], warningstext, warnings);
        //printf("\n\n%s", warningstext);
    }


    retcode = TH260_SetStopOverflow(dev[0],
        0, 10000); //for example only
    if (retcode < 0)
    {
        TH260_GetErrorString(Errorstring, retcode);
        printf("\nTH260_SetStopOverflow error %d (%s). Aborted.\n", retcode, Errorstring);
        ex(outputDir, xPos, yPos);
    }

    cmd = 0;
    while (cmd != 'q')
    {

        retcode = TH260_ClearHistMem(dev[0]);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_ClearHistMem error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        //printf("\npress RETURN to start measurement");=================================================================================================================================
        //getchar()=======================================================================

        retcode = TH260_GetSyncRate(dev[0], &Syncrate);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_GetSyncRate error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }
        //printf("\nSyncrate=%d/s", Syncrate);

        for (i = 0; i < NumChannels; i++) // for all channels
        {
            retcode = TH260_GetCountRate(dev[0], i, &Countrate);
            if (retcode < 0)
            {
                //TH260_GetErrorString(Errorstring, retcode);
                //printf("\nTH260_GetCountRate error %d (%s). Aborted.\n", retcode, Errorstring);
                ex(outputDir, xPos, yPos);
            }
            //printf("\nCountrate[%d]=%d/s", i, Countrate);
        }

        //here you could check for warnings again

        retcode = TH260_StartMeas(dev[0], Tacq);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_StartMeas error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        //printf("\n\nMeasuring for %d milliseconds...", Tacq);

        ctcstatus = 0;
        while (ctcstatus == 0)
        {
            retcode = TH260_CTCStatus(dev[0], &ctcstatus);
            if (retcode < 0)
            {
                TH260_GetErrorString(Errorstring, retcode);
                printf("\nTH260_CTCStatus error %d (%s). Aborted.\n", retcode, Errorstring);
                ex(outputDir, xPos, yPos);
            }
        }

        retcode = TH260_StopMeas(dev[0]);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_StopMeas error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        //printf("\n");
        for (i = 0; i < NumChannels; i++) // for all channels
        {
            retcode = TH260_GetHistogram(dev[0], counts[i], i, 1);
            if (retcode < 0)
            {
                TH260_GetErrorString(Errorstring, retcode);
                printf("\nTH260_GetHistogram error %d (%s). Aborted.\n", retcode, Errorstring);
                ex(outputDir, xPos, yPos);
            }

            Integralcount = 0;
            for (j = 0; j < HistLen; j++)
                Integralcount += counts[i][j];

            //printf("\n  Integralcount[%1d]=%1.0lf", i, Integralcount);

        }
        //printf("\n");

        retcode = TH260_GetFlags(dev[0], &flags);
        if (retcode < 0)
        {
            TH260_GetErrorString(Errorstring, retcode);
            printf("\nTH260_GetFlags error %d (%s). Aborted.\n", retcode, Errorstring);
            ex(outputDir, xPos, yPos);
        }

        if (flags & FLAG_OVERFLOW) printf("\n  Overflow.");

        //printf("\nEnter c to continue or q to quit and save the count data.");
        cmd = 'q';
        //getchar();
    }

    for (j = 0; j < 2000; j++)
    {
        for (i = 0; i < NumChannels; i++)
            fprintf(fpout, "%5d ", counts[i][j]);
        fprintf(fpout, "\n");
    }
    fclose(fpout);
    return(0);
};

// closes tcspc board, also reinitializes board and retakes measurements in case of an error
unsigned int* ex(string outputDir, int xPos, int yPos) {
    errorCount += 1;
    printf("%d", errorCount);
    if (errorCount > 4) { 
        for (i = 0; i < MAXDEVNUM; i++) //no harm to close all
        {
            TH260_CloseDevice(i);
            printf("closed the device");
        }
        
        abort;
    }//limits number of errors to 5 in case of repeatin error, preventing infinite loops
    else {

        for (i = 0; i < MAXDEVNUM; i++) //no harm to close all
        {
            TH260_CloseDevice(i);
            printf("closed the device ");
        }
              
        if (StageCode == "measure") {
            Initialize(outputDir, xPos, yPos);
            measure(outputDir, xPos, yPos);
        }
        if (StageCode == "End of Line") {
            for (i = 0; i < MAXDEVNUM; i++) //no harm to close all
            {
                TH260_CloseDevice(i);
                printf("closed the device");
            }
        }
    }

    return(0);
}

//main code
int main() {
    std::cout << "OK ready\n" << std::flush;
    std::string line;
    try {
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            std::istringstream iss(line);
            std::string cmd; iss >> cmd;

            if (cmd == "init") {
                int ix, iy; string outputDir; iss >> outputDir >> ix >> iy;
                Initialize(outputDir, ix, iy);
                std::cout << "OK\n";
            }

            else if (cmd == "measure") {
                int ix, iy, t_acq; string outputDir; float wavelength;  iss >> outputDir >> ix >> iy >> wavelength >> t_acq;
                wl = wavelength;
                Tacq = t_acq;
                measure(outputDir, ix, iy);
                std::cout << "OK\n";
            }

            else if (cmd == "exit") {
                StageCode = "End of Line";
                int ix, iy; string outputDir; iss >> outputDir >> ix >> iy;
                ex(outputDir, ix, iy);
                std::cout << "OK\n";
            }

            else {
                std::cout << "ERR unknown_cmd\n";
            }

            std::cout.flush();
        }
    }
    catch (const std::exception& e) {
        std::cout << "ERR " << e.what() << "\n";
    }

    return 0;
}