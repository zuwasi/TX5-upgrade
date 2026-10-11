/* SPDX-License-Identifier: MIT */
#include "tx_api.h"
#include "qemu_board.h"

static TX_QUEUE queue;
static ULONG queue_storage[4];
static TX_SEMAPHORE semaphore;
static TX_MUTEX mutex;
static TX_EVENT_FLAGS_GROUP flags;
static TX_THREAD worker;
static ULONG worker_stack[256];
static TX_BYTE_POOL pool;
static ULONG pool_storage[128];
/* Tracked by the application so the check does not depend on scheduler
   internals that differ between ThreadX generations. */
static volatile ULONG worker_progress;

static void require(bool passed, const char *reason)
{
    if (!passed) {
        qemu_report_failure(reason);
    }
}

static void worker_entry(ULONG input)
{
    ULONG value = 0U;
    (void)input;
    worker_progress = 1U;
    require(tx_queue_receive(&queue, &value, TX_WAIT_FOREVER) == TX_SUCCESS,
            "blocking queue receive");
    worker_progress = 2U;
    require(value == 0x1234U, "queue payload");
    require(tx_event_flags_set(&flags, 1U, TX_OR) == TX_SUCCESS, "event set");
}

void rtos_selftest(void)
{
    ULONG message = 0x1234U;
    ULONG actual = 0U;
    void *memory = TX_NULL;

    require(tx_queue_create(&queue, "test-queue", TX_1_ULONG, queue_storage,
                sizeof(queue_storage)) == TX_SUCCESS, "queue create");
    require(tx_event_flags_create(&flags, "test-flags") == TX_SUCCESS, "event create");
    require(tx_thread_create(&worker, "test-worker", worker_entry, 0U,
                worker_stack, sizeof(worker_stack), 4U, 4U,
                TX_NO_TIME_SLICE, TX_AUTO_START) == TX_SUCCESS, "worker create");
    /* The higher-priority worker preempts, then suspends on the empty queue.
       This send resumes it, triggers another switch, and it sets our flag. */
    require(worker_progress == 1U, "worker preempted and suspended on empty queue");
    require(tx_queue_send(&queue, &message, TX_NO_WAIT) == TX_SUCCESS, "queue send");
    require(worker_progress == 2U, "worker resumed after queue suspension");
    require(tx_event_flags_get(&flags, 1U, TX_OR_CLEAR, &actual, TX_NO_WAIT)
                == TX_SUCCESS && actual == 1U, "event receive");
    require(tx_semaphore_create(&semaphore, "test-sem", 1U) == TX_SUCCESS,
            "semaphore create");
    require(tx_semaphore_get(&semaphore, TX_NO_WAIT) == TX_SUCCESS, "semaphore get");
    require(tx_semaphore_get(&semaphore, TX_NO_WAIT) == TX_NO_INSTANCE,
            "empty semaphore error");
    require(tx_semaphore_put(&semaphore) == TX_SUCCESS, "semaphore put");
    require(tx_mutex_create(&mutex, "test-mutex", TX_INHERIT) == TX_SUCCESS,
            "mutex create");
    require(tx_mutex_get(&mutex, TX_NO_WAIT) == TX_SUCCESS, "mutex get");
    require(tx_mutex_put(&mutex) == TX_SUCCESS, "mutex put");
    require(tx_byte_pool_create(&pool, "test-pool", pool_storage,
                sizeof(pool_storage)) == TX_SUCCESS, "pool create");
    require(tx_byte_allocate(&pool, &memory, 64U, TX_NO_WAIT) == TX_SUCCESS,
            "pool allocate");
    require(tx_byte_release(memory) == TX_SUCCESS, "pool release");
    qemu_metric("worker_thread_runs", worker.tx_thread_run_count);
    qemu_write("[selftest] queue/preemption/events/semaphore/mutex/byte-pool PASS\n");
}
