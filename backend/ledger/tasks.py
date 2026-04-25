from celery import shared_task
from django.db import transaction
from django.utils import timezone
import random
import logging

from .models import Payout, LedgerEntry

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_pending_payouts(self):
    """
    Background task to process pending payouts.

    This task:
    1. Picks up pending payouts
    2. Simulates bank settlement (70% succeed, 20% fail, 10% stuck)
    3. Updates payout status accordingly
    4. Releases or returns held funds atomically
    """
    logger.info("Processing pending payouts...")

    # Get all pending payouts
    pending_payouts = Payout.objects.filter(status='PENDING')

    if not pending_payouts.exists():
        logger.info("No pending payouts to process.")
        return

    processed_count = 0
    for payout in pending_payouts:
        try:
            # Move to PROCESSING state
            payout.status = 'PROCESSING'
            payout.last_retry_at = timezone.now()
            payout.save()

            # Simulate bank settlement with randomness
            # 70% succeed, 20% fail, 10% remain stuck in processing
            outcome = random.random()

            if outcome < 0.7:
                # Success - complete the payout
                complete_payout(payout)
                processed_count += 1
            elif outcome < 0.9:
                # Failure - return funds to merchant
                fail_payout(payout, "Bank settlement failed")
                processed_count += 1
            else:
                # Stuck in processing - will be retried
                logger.info(f"Payout {payout.id} stuck in processing, will retry later")

        except Exception as e:
            logger.error(f"Error processing payout {payout.id}: {str(e)}")
            # Leave in processing state for retry

    logger.info(f"Processed {processed_count} payouts")


@shared_task(bind=True, max_retries=3)
def retry_stuck_payouts(self):
    """
    Background task to retry payouts stuck in processing state.

    Implements exponential backoff:
    - Retry after 2^retry_count seconds (max 30 seconds)
    - Maximum 3 attempts
    - Then move to failed and return funds
    """
    logger.info("Checking for stuck payouts...")

    # Get payouts in processing state
    stuck_payouts = Payout.objects.filter(status='PROCESSING')

    retried_count = 0
    for payout in stuck_payouts:
        if payout.should_retry():
            logger.info(f"Retrying payout {payout.id}, attempt {payout.retry_count + 1}")

            try:
                # Increment retry count
                payout.retry_count += 1
                payout.last_retry_at = timezone.now()

                if payout.retry_count >= payout.max_retries:
                    # Max retries reached, fail the payout
                    fail_payout(payout, f"Max retries ({payout.max_retries}) exceeded")
                    logger.warning(f"Payout {payout.id} failed after {payout.retry_count} retries")
                else:
                    # Try again with simulated bank settlement
                    outcome = random.random()

                    if outcome < 0.7:
                        # Success
                        complete_payout(payout)
                        logger.info(f"Payout {payout.id} completed on retry {payout.retry_count}")
                    elif outcome < 0.9:
                        # Failure
                        fail_payout(payout, "Bank settlement failed during retry")
                        logger.info(f"Payout {payout.id} failed on retry {payout.retry_count}")
                    else:
                        # Still stuck, save for next retry
                        payout.save()
                        logger.info(f"Payout {payout.id} still stuck, will retry again")

                retried_count += 1

            except Exception as e:
                logger.error(f"Error retrying payout {payout.id}: {str(e)}")

    logger.info(f"Retried {retried_count} stuck payouts")


def complete_payout(payout):
    """
    Complete a payout successfully.

    This atomically:
    1. Updates payout status to COMPLETED
    2. Converts held debit to final debit
    """
    with transaction.atomic():
        # Update payout status
        payout.status = 'COMPLETED'
        payout.save()

        # Find the held debit entry and convert it to final
        held_entry = LedgerEntry.objects.filter(
            payout=payout,
            entry_type='DEBIT',
            is_held=True
        ).first()

        if held_entry:
            # Convert held debit to final debit
            held_entry.is_held = False
            held_entry.description = f"Payout completed - {held_entry.description}"
            held_entry.save()

        logger.info(f"Payout {payout.id} completed successfully")


def fail_payout(payout, reason):
    """
    Fail a payout and return held funds to merchant balance.

    This atomically:
    1. Updates payout status to FAILED
    2. Deletes the held debit entry (returns funds to balance)
    3. Sets failure reason
    """
    with transaction.atomic():
        # Update payout status
        payout.status = 'FAILED'
        payout.failure_reason = reason
        payout.save()

        # Delete the held debit entry to return funds
        held_entry = LedgerEntry.objects.filter(
            payout=payout,
            entry_type='DEBIT',
            is_held=True
        ).first()

        if held_entry:
            held_entry.delete()
            logger.info(f"Returned funds to merchant {payout.merchant.id} for failed payout {payout.id}")

        logger.info(f"Payout {payout.id} failed: {reason}")


@shared_task
def initialize_payout_processor():
    """
    Initialize the payout processor by scheduling periodic tasks.
    This should be called on application startup.
    """
    # Process pending payouts every 10 seconds
    process_pending_payouts.delay()

    # Retry stuck payouts every 30 seconds
    retry_stuck_payouts.delay()
