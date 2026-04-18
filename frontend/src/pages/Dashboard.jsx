import DashboardPage from '@/components/dashboard/DashboardPage';

/**
 * SecuriSphere dashboard — delegates to `DashboardPage` (triage / grid / story variants).
 */
export default function Dashboard(props) {
  return <DashboardPage {...props} />;
}
