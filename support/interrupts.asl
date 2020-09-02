////////////////////////////////////////////////////////////////
// Functions to support interrupts and System Errors
//
// The following functions are not defined in the current
// XML release but are necessary to build a working simulator
////////////////////////////////////////////////////////////////

boolean __PendingPhysicalSError;
boolean __PendingVirtualSError;
boolean __PendingInterrupt;

__ResetInterruptState()
    __PendingPhysicalSError = FALSE;
    __PendingInterrupt = FALSE;

SendEvent()
    SendEventLocal();
    return;

boolean InsertIESBBeforeException(bits(2) el)
    return FALSE;

SynchronizeErrors()
    return;

SetInterruptRequestLevel(InterruptID id, signal level)
    assert FALSE;

AArch32.SErrorSyndrome AArch32.PhysicalSErrorSyndrome()
    assert FALSE;
    AArch32.SErrorSyndrome r;
    r.AET = Zeros(2);
    r.ExT = Zeros(1);
    return r;

bits(25) AArch64.PhysicalSErrorSyndrome(boolean implicit_esb)
    assert FALSE;
    return Zeros(25);

__SetPendingPhysicalSError()
    __PendingPhysicalSError = TRUE;
    return;

ClearPendingPhysicalSError()
    __PendingPhysicalSError = FALSE;
    return;

boolean IsPhysicalSErrorPending()
    return __PendingPhysicalSError;

boolean IsSynchronizablePhysicalSErrorPending()
    return FALSE; // TODO

__SetPendingVirtualSError()
    __PendingVirtualSError = TRUE;
    return;

ClearPendingVirtualSError()
    __PendingVirtualSError = FALSE;
    return;

boolean IsVirtualSErrorPending()
    return __PendingVirtualSError;

TakeUnmaskedPhysicalSErrorInterrupts(boolean iesb_req)
    assert FALSE;

TakeUnmaskedSErrorInterrupts()
    assert FALSE;

boolean IRQPending()
    return FALSE;

boolean FIQPending()
    return FALSE;

////////////////////////////////////////////////////////////////
// End
////////////////////////////////////////////////////////////////
