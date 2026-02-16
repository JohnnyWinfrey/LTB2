// stage_helper_dynamic.cpp
// Build: x64 Console (/std:c++17). No Kinesis import libs needed.
// Put these DLLs next to the EXE (or on PATH):
//   - Thorlabs.MotionControl.DeviceManager.dll  (or Thorlabs.MotionControl.TLI.dll)
//   - Thorlabs.MotionControl.KCube.Piezo.dll
//
// Line protocol (stdin/stdout, one command per line):
//   open                      -> uses DEFAULT_SX/DEFAULT_SY, vmax=750 (7.50 V)
//   open <vmax_tenths>        -> uses defaults, sets max output voltage
//   open <sx> <sy>            -> explicit serials, vmax=750
//   open <sx> <sy> <vmax>     -> explicit serials + vmax
//   status                    -> OK X=<0|1> Y=<0|1>  (1 = connected)
//   setdac <vx> <vy>          -> set raw DAC codes 0..32767
//   move_ix <ix> <iy> <w> <h> -> map pixel index to DAC (0..w-1 / 0..h-1)
//   disable                   -> disable & close both devices
//   exit                      -> OK bye (then quits)

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

// ---------- Hardcoded serials (edit to yours) ----------
static const char* SX = "29503259";  // X-axis KCube serial
static const char* SY = "29500307";  // Y-axis KCube serial
// ------------------------------------------------------

static bool g_open = false;

static void stage_open()
{
    const char* stageOne = "29503259";
    const char* stageTwo = "29500307";
    char serialNos[100];
    TLI_BuildDeviceList();
    TLI_GetDeviceListSize();
    TLI_GetDeviceListByTypeExt(serialNos, 100, 81);

    // output list of matching devices
    {
        char* searchContext = nullptr;
        char* p = strtok_s(serialNos, ",", &searchContext);

        while (p != nullptr)
        {
            TLI_DeviceInfo deviceInfo;
            // get device info from device
            TLI_GetDeviceInfo(p, &deviceInfo);
            // get strings from device info structure
            char desc[65];
            strncpy_s(desc, deviceInfo.description, 64);
            desc[64] = '\0';
            char serialNo[9];
            strncpy_s(serialNo, deviceInfo.serialNo, 8);
            serialNo[8] = '\0';
            // output
            printf("Found Device %s=%s : %s\r\n", p, serialNo, desc);
            p = strtok_s(nullptr, ",", &searchContext);
        }
    }
    int T = PCC_Open(stageOne);
    int T2 = PCC_Open(stageTwo);

    printf("OK \n");
    //printf("Hey there, handsome.");

    bool connecheck = PCC_StartPolling(stageOne, 200);
    //printf("%d \n", connecheck);
    connecheck = PCC_CheckConnection(stageOne);
    //printf("%d \n", connecheck);

    connecheck = PCC_Enable(stageOne);
    //printf("%d \n", connecheck);

    connecheck = PCC_SetMaxOutputVoltage(stageOne, 750);
    //printf("%d \n", connecheck);

    connecheck = PCC_StartPolling(stageTwo, 200);
    //printf("%d \n", connecheck);
    connecheck = PCC_CheckConnection(stageTwo);
    //printf("%d \n", connecheck);

    connecheck = PCC_Enable(stageTwo);
    //printf("%d \n", connecheck);

    connecheck = PCC_SetMaxOutputVoltage(stageTwo, 750);
    //printf("%d \n", connecheck);

    short voltsOne = 0 * 32767 / 75;
    short voltsTwo = 0 * 32767 / 75;

    connecheck = PCC_SetOutputVoltage(stageTwo, voltsTwo);
    connecheck = PCC_SetOutputVoltage(stageOne, voltsOne);
    g_open = true;
}

static void stage_move_ix(int ix, int iy, int w, int h)
{
    if (!g_open) throw std::runtime_error("stage not open");
    // Map [0..w-1] / [0..h-1] ? [0..32767]
    short vx = short((w > 0) ? (ix * 32767 / (w)) : 0); // Change this to a real width and height you want to travel then multiply by a percentage to achieve that
    short vy = short((h > 0) ? (iy * 32767 / (h)) : 0);
    PCC_SetOutputVoltage(SX, vx);
    PCC_SetOutputVoltage(SY, vy);
    printf("OK");
}

static void stage_reset(int ix, int w)
{

    do {
        //setting  stage voltage
        short vx = short((w > 0) ? (ix * 32767 / (w)) : 0);
        bool connecheck = PCC_SetOutputVoltage(SX, vx);
        //printf("%d", connecheck);
        ix -= 1;
    } while (ix >= 0);
}

int main()
{
    std::cout << "OK ready\n" << std::flush;
    std::string line;
    try {
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;
            std::istringstream iss(line);
            std::string cmd; iss >> cmd;

            if (cmd == "exit" || cmd == "quit") {
                std::cout << "OK bye\n";
                break;
            }
            else if (cmd == "open") {

                stage_open();
                std::cout << "OK\n";
            }

            else if (cmd == "move_ix") {
                int ix, iy, w, h; iss >> ix >> iy >> w >> h;
                stage_move_ix(ix, iy, w, h);
                std::cout << "OK\n";
            }
            else if (cmd == "stage_reset") {
                int ix, w; iss >> ix >> w;
                stage_reset(ix, w);
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
