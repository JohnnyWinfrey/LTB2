// th260_helper_ultra.cpp -- TimeHarp 260 TCSPC helper.
//
// Line protocol over stdin/stdout, one command in -> one response line out,
// matching hardware_controllers._LineProcess:
//
//   init                     -> OK RES=<ps> CH=<n> LEN=<histlen>
//   info                     -> OK RES=<ps> CH=<n> LEN=<histlen>
//   measure <tacq_ms> <bins> -> OK RES=<ps> CH=<n> LEN=<histlen> SYNC=<hz>
//                                  CR=<c0>,<c1> OVF=<0|1>
//                                  DATA=<ch0 bins,...>;<ch1 bins,...>
//   exit                     -> OK
//
// Anything else -> "ERR <reason>". The histogram is returned to Python, which
// owns saving it (see th260_helpers.saveTCSPCHDF5); this helper writes no files.
//
// stdout is the protocol channel and carries NOTHING but response lines --
// every diagnostic goes to stderr, or it would desync the client.
//
// Build: see helpers/build.sh (mingw cross-build for Windows, or a native
// build against th260_stub.cpp for local protocol testing).

#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>

#include "th260_compat.h"

// ---------------------------------------------------------------------------
// Acquisition settings. Compile-time, as before -- only tacq and bins are
// settable at runtime.
// ---------------------------------------------------------------------------
static int Binning = 3;      // 0 => 0.025 ns bins, 1 => 0.05, 2 => 0.1, 3 => 0.2
static int Offset = 0;
static int SyncOffset = 25000;
static int SyncDivider = 1;

// TimeHarp 260 P boards (picosecond)
static int SyncCFDZeroCross = -10;
static int SyncCFDLevel = -100;
static int InputCFDZeroCross = -10;
static int InputCFDLevel = -30;  // -30 for monochromator/PMT, -100 for SPAD

// TimeHarp 260 N boards (nanosecond)
static int SyncTriggerEdge = 0;
static int SyncTriggerLevel = -50;
static int InputTriggerEdge = 0;
static int InputTriggerLevel = -50;

// ---------------------------------------------------------------------------
// Device state
// ---------------------------------------------------------------------------
static unsigned int counts[MAXINPCHAN][MAXHISTLEN];

static int devIdx = -1;      // index of the opened device, -1 => not open
static int NumChannels = 0;
static int HistLen = 0;
static double Resolution = 0.0;

static int Syncrate = 0;
static int Countrate[MAXINPCHAN];
static bool Overflow = false;

static char HW_Model[16];
static char HW_Partno[8];
static char HW_Version[16];
static char HW_Serial[8];

static std::string lastError;

// Record a library failure as a readable message and bail out of the caller.
static bool fail(const char* what, int code) {
    char errstring[40] = {0};
    TH260_GetErrorString(errstring, code);
    std::ostringstream os;
    os << what << " failed (" << code << ": " << errstring << ")";
    lastError = os.str();
    std::fprintf(stderr, "%s\n", lastError.c_str());
    return false;
}

#define TH_TRY(expr, what)                     \
    do {                                       \
        int rc_ = (expr);                      \
        if (rc_ < 0) return fail(what, rc_);   \
    } while (0)

static void closeAllDevices() {
    for (int i = 0; i < MAXDEVNUM; i++) TH260_CloseDevice(i);  // no harm to close all
    devIdx = -1;
}

// ---------------------------------------------------------------------------
// Initialize the board. Returns false and sets lastError on failure -- the old
// version recursively retried from an error handler with a counter it never
// reset, which meant a long scan silently died after five cumulative errors.
// Errors now propagate to the client as ERR, which is recoverable in Python.
// ---------------------------------------------------------------------------
static bool initialize() {
    if (devIdx >= 0) closeAllDevices();

    int found = -1;
    for (int i = 0; i < MAXDEVNUM; i++) {
        if (TH260_OpenDevice(i, HW_Serial) == 0) {  // grab the first one we can open
            found = i;
            break;
        }
    }
    if (found < 0) {
        lastError = "no_device_available";
        std::fprintf(stderr, "no TH260 device available\n");
        return false;
    }
    devIdx = found;
    std::fprintf(stderr, "using device #%d (serial %s)\n", devIdx, HW_Serial);

    TH_TRY(TH260_Initialize(devIdx, MODE_HIST), "TH260_Initialize");  // histogram mode, internal clock
    TH_TRY(TH260_GetHardwareInfo(devIdx, HW_Model, HW_Partno, HW_Version), "TH260_GetHardwareInfo");
    TH_TRY(TH260_GetNumOfInputChannels(devIdx, &NumChannels), "TH260_GetNumOfInputChannels");
    if (NumChannels > MAXINPCHAN) NumChannels = MAXINPCHAN;
    TH_TRY(TH260_SetSyncDiv(devIdx, SyncDivider), "TH260_SetSyncDiv");

    if (strcmp(HW_Model, "TimeHarp 260 P") == 0) {  // picosecond resolving board
        TH_TRY(TH260_SetSyncCFD(devIdx, SyncCFDLevel, SyncCFDZeroCross), "TH260_SetSyncCFD");
        for (int i = 0; i < NumChannels; i++)  // same input settings for all channels
            TH_TRY(TH260_SetInputCFD(devIdx, i, InputCFDLevel, InputCFDZeroCross), "TH260_SetInputCFD");
    }

    if (strcmp(HW_Model, "TimeHarp 260 N") == 0) {  // nanosecond resolving board
        TH_TRY(TH260_SetSyncEdgeTrg(devIdx, SyncTriggerLevel, SyncTriggerEdge), "TH260_SetSyncEdgeTrg");
        for (int i = 0; i < NumChannels; i++)
            TH_TRY(TH260_SetInputEdgeTrg(devIdx, i, InputTriggerLevel, InputTriggerEdge), "TH260_SetInputEdgeTrg");
    }

    TH_TRY(TH260_SetSyncChannelOffset(devIdx, SyncOffset), "TH260_SetSyncChannelOffset");
    for (int i = 0; i < NumChannels; i++)  // same input offset for all channels
        TH_TRY(TH260_SetInputChannelOffset(devIdx, i, 0), "TH260_SetInputChannelOffset");

    TH_TRY(TH260_SetHistoLen(devIdx, MAXLENCODE, &HistLen), "TH260_SetHistoLen");
    TH_TRY(TH260_SetBinning(devIdx, Binning), "TH260_SetBinning");
    TH_TRY(TH260_SetOffset(devIdx, Offset), "TH260_SetOffset");
    TH_TRY(TH260_GetResolution(devIdx, &Resolution), "TH260_GetResolution");
    TH_TRY(TH260_SetStopOverflow(devIdx, 0, 10000), "TH260_SetStopOverflow");

    std::fprintf(stderr, "model %s, %d channels, %d bins, %1.0lf ps\n",
                 HW_Model, NumChannels, HistLen, Resolution);
    return true;
}

// ---------------------------------------------------------------------------
// One acquisition into counts[][]. Fills Syncrate / Countrate / Overflow.
// ---------------------------------------------------------------------------
static bool measure(int tacq_ms) {
    if (devIdx < 0) {
        lastError = "not_initialized";
        return false;
    }

    TH_TRY(TH260_ClearHistMem(devIdx), "TH260_ClearHistMem");
    TH_TRY(TH260_GetSyncRate(devIdx, &Syncrate), "TH260_GetSyncRate");
    for (int i = 0; i < NumChannels; i++)
        TH_TRY(TH260_GetCountRate(devIdx, i, &Countrate[i]), "TH260_GetCountRate");

    int warnings = 0;
    TH_TRY(TH260_GetWarnings(devIdx, &warnings), "TH260_GetWarnings");
    if (warnings) {
        char warningstext[16384] = {0};  // library requires a 16384-byte buffer
        TH260_GetWarningsText(devIdx, warningstext, warnings);
        std::fprintf(stderr, "%s\n", warningstext);
    }

    TH_TRY(TH260_StartMeas(devIdx, tacq_ms), "TH260_StartMeas");
    int ctcstatus = 0;
    while (ctcstatus == 0)
        TH_TRY(TH260_CTCStatus(devIdx, &ctcstatus), "TH260_CTCStatus");
    TH_TRY(TH260_StopMeas(devIdx), "TH260_StopMeas");

    for (int i = 0; i < NumChannels; i++)
        TH_TRY(TH260_GetHistogram(devIdx, counts[i], i, 1), "TH260_GetHistogram");

    int flags = 0;
    TH_TRY(TH260_GetFlags(devIdx, &flags), "TH260_GetFlags");
    Overflow = (flags & FLAG_OVERFLOW) != 0;
    if (Overflow) std::fprintf(stderr, "overflow\n");

    return true;
}

// "RES=<ps> CH=<n> LEN=<bins>" -- shared by init and info.
static std::string infoFields() {
    std::ostringstream os;
    os << "RES=" << Resolution << " CH=" << NumChannels << " LEN=" << HistLen;
    return os.str();
}

int main() {
    std::cout << "OK ready\n" << std::flush;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        std::istringstream iss(line);
        std::string cmd;
        iss >> cmd;

        if (cmd == "init") {
            if (initialize()) std::cout << "OK " << infoFields() << "\n";
            else              std::cout << "ERR " << lastError << "\n";

        } else if (cmd == "info") {
            if (devIdx < 0) std::cout << "ERR not_initialized\n";
            else            std::cout << "OK " << infoFields() << "\n";

        } else if (cmd == "measure") {
            int tacq_ms = 5000, bins = 2000;
            iss >> tacq_ms >> bins;
            if (bins <= 0 || bins > HistLen) bins = HistLen;  // clamp to what the board holds

            if (!measure(tacq_ms)) {
                std::cout << "ERR " << lastError << "\n";
            } else {
                std::ostringstream os;
                os << "OK " << infoFields() << " SYNC=" << Syncrate << " CR=";
                for (int i = 0; i < NumChannels; i++) {
                    if (i) os << ',';
                    os << Countrate[i];
                }
                os << " OVF=" << (Overflow ? 1 : 0) << " DATA=";
                for (int i = 0; i < NumChannels; i++) {
                    if (i) os << ';';
                    for (int j = 0; j < bins; j++) {
                        if (j) os << ',';
                        os << counts[i][j];
                    }
                }
                std::cout << os.str() << "\n";
            }

        } else if (cmd == "exit") {
            closeAllDevices();
            std::cout << "OK\n" << std::flush;
            return 0;

        } else {
            std::cout << "ERR unknown_cmd\n";
        }

        std::cout.flush();
    }

    closeAllDevices();
    return 0;
}
