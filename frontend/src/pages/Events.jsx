import EventsPage from '@/components/events/EventsPage';

/**
 * SecuriSphere events route — delegates to `EventsPage` (table + timeline variants).
 */
export default function Events(props) {
  return <EventsPage {...props} />;
}
