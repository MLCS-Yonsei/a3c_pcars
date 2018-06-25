// Used for memory-mapped functionality
#include <windows.h>
#include "sharedmemory.h"

// Used for this example
#include <stdio.h>
#include <conio.h>

// Name of the pCars memory mapped file
#define MAP_OBJECT_NAME "$pcars$"

int main()
{
	// Open the memory-mapped file
	HANDLE fileHandle = OpenFileMapping( PAGE_READONLY, FALSE, MAP_OBJECT_NAME );
	if (fileHandle == NULL)
	{
		printf( "Could not open file mapping object (%d).\n", GetLastError() );
		return 1;
	}

	// Get the data structure
	const SharedMemory* sharedData = (SharedMemory*)MapViewOfFile( fileHandle, PAGE_READONLY, 0, 0, sizeof(SharedMemory) );
	if (sharedData == NULL)
	{
		printf( "Could not map view of file (%d).\n", GetLastError() );

		CloseHandle( fileHandle );
		return 1;
	}

	// Ensure we're sync'd to the correct data version
	if ( sharedData->mVersion != SHARED_MEMORY_VERSION )
	{
		printf( "Data version mismatch\n");
		return 1;
	}

	//------------------------------------------------------------------------------
	// TEST DISPLAY CODE
	//------------------------------------------------------------------------------
	printf( "ESC TO EXIT\n\n", sharedData->mUnfilteredSteering );
	while (true)
	{
		const bool isValidParticipantIndex = sharedData->mViewedParticipantIndex != -1 && sharedData->mViewedParticipantIndex < sharedData->mNumParticipants && sharedData->mViewedParticipantIndex < STORED_PARTICIPANTS_MAX;
		if ( isValidParticipantIndex )
		{
			const ParticipantInfo& viewedParticipantInfo = sharedData->mParticipantInfo[sharedData->mViewedParticipantIndex];
			printf( "mParticipantName: (%s)\n", viewedParticipantInfo.mName );
			printf( "lap Distance = %f \n", viewedParticipantInfo.mCurrentLapDistance );
			printf( "mWorldPosition: (%f,%f,%f)\n", viewedParticipantInfo.mWorldPosition[0], viewedParticipantInfo.mWorldPosition[1], viewedParticipantInfo.mWorldPosition[2] );
		}
		printf( "mGameState: (%d)\n", sharedData->mGameState );
		printf( "mSessionState: (%d)\n", sharedData->mSessionState );
		printf( "mRaceState: (%d)\n", sharedData->mRaceState );

		system("cls");

		if ( _kbhit() && _getch() == 27 ) // check for escape
		{
			break;
		}
	}
	//------------------------------------------------------------------------------

	// Cleanup
	UnmapViewOfFile( sharedData );
	CloseHandle( fileHandle );

	return 0;
}
