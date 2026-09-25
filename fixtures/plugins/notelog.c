/* Test fixture plugin for the PLUGINS end-to-end tests.
 *
 *   clang -dynamiclib -I ../npp/macos/plugin-sdk [-DPLUGIN_NAME='"X"'] -o X.dylib notelog.c
 *
 * - every NPPN_* notification is appended, one code per line, to
 *   <NPPM_GETPLUGINSCONFIGDIR>/<PLUGIN_NAME>.log (written and flushed at once);
 * - its commands write NPPM answers into the document (SCI_REPLACESEL), and
 *   "Open Other" opens the path written in <config>/open.txt (NPPM_DOOPEN),
 *   "Save Current" saves (NPPM_SAVECURRENTFILE); both append "doopen=N" /
 *   "save=N" to the log.
 */
#include "NotepadMacPlugin.h"
#include <stdio.h>
#include <string.h>

#ifndef PLUGIN_NAME
#define PLUGIN_NAME "NoteLog"
#endif
#define SCI_REPLACESEL 2170

static NppMacData npp;

static void configPath(char *out, size_t size, const char *leaf)
{
    char dir[2048] = "";
    npp.send(npp.nppHandle, NPPM_GETPLUGINSCONFIGDIR, sizeof dir, (intptr_t)dir);
    snprintf(out, size, "%s/%s", dir, leaf);
}

static void logLine(const char *line)
{
    char path[2300];
    configPath(path, sizeof path, PLUGIN_NAME ".log");
    FILE *f = fopen(path, "a");
    if (!f) return;
    fprintf(f, "%s\n", line);
    fclose(f);
}

static void insert(const char *text) { npp.send(npp.scintillaHandle, SCI_REPLACESEL, 0, (intptr_t)text); }

static void insertGreeting(void) { insert("hello from " PLUGIN_NAME); }

static void insertAnswer(uint32_t message)
{
    char buffer[2048] = "";
    npp.send(npp.nppHandle, message, sizeof buffer, (intptr_t)buffer);
    insert(buffer);
}
static void insertFullPath(void) { insertAnswer(NPPM_GETFULLCURRENTPATH); }
static void insertDirectory(void) { insertAnswer(NPPM_GETCURRENTDIRECTORY); }
static void insertFileName(void) { insertAnswer(NPPM_GETFILENAME); }

static void insertVersion(void)
{
    char buffer[64];
    snprintf(buffer, sizeof buffer, "%ld", (long)npp.send(npp.nppHandle, NPPM_GETNPPVERSION, 0, 0));
    insert(buffer);
}

static void openOther(void)
{
    char path[2300], target[2048] = "", line[64];
    configPath(path, sizeof path, "open.txt");
    FILE *f = fopen(path, "r");
    if (f) { if (!fgets(target, sizeof target, f)) target[0] = 0; fclose(f); }
    target[strcspn(target, "\r\n")] = 0;
    snprintf(line, sizeof line, "doopen=%ld", (long)npp.send(npp.nppHandle, NPPM_DOOPEN, 0, (intptr_t)target));
    logLine(line);
}

static void saveCurrent(void)
{
    char line[64];
    snprintf(line, sizeof line, "save=%ld", (long)npp.send(npp.nppHandle, NPPM_SAVECURRENTFILE, 0, 0));
    logLine(line);
}

static NppMacFuncItem items[] = {
    { "Insert Greeting",  insertGreeting },
    { "",                 0 },
    { "Insert File Name", insertFileName },
    { "Insert Full Path", insertFullPath },
    { "Insert Directory", insertDirectory },
    { "Insert Version",   insertVersion },
    { "Open Other",       openOther },
    { "Save Current",     saveCurrent },
};

void nppmac_setInfo(NppMacData data) { npp = data; }
const char *nppmac_getName(void) { return PLUGIN_NAME; }

NppMacFuncItem *nppmac_getFuncsArray(int *count)
{
    *count = (int)(sizeof(items) / sizeof(items[0]));
    return items;
}

void nppmac_beNotified(const NppMacNotification *notification)
{
    char line[32];
    snprintf(line, sizeof line, "%u", (unsigned)notification->code);
    logLine(line);
}
