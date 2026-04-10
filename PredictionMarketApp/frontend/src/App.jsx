import React, { useEffect, useState } from 'react';
import useAppStore from './store/useAppStore';
import SentimentStrip from './components/SentimentStrip/SentimentStrip';
import TopNav from './components/Nav/TopNav';
import BottomNav from './components/Nav/BottomNav';
import BotListPanel from './components/BotList/BotListPanel';
import RuleEditor from './components/RuleEditor/RuleEditor';
import SimulatorPanel from './components/Simulator/SimulatorPanel';
import MarketBrowser from './components/MarketBrowser/MarketBrowser';
import TradeLog from './components/TradeLog/TradeLog';
import PortfolioScreen from './components/Portfolio/PortfolioScreen';
import SettingsScreen from './components/Settings/SettingsScreen';
import VarsPanel from './components/Vars/VarsPanel';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-3 p-4">
          <p className="text-sm text-terminal-red-text font-mono text-center">
            [ ERROR IN {(this.props.name || 'COMPONENT').toUpperCase()} ]
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="btn-primary text-xs"
          >
            RELOAD
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const { activeTab, setActiveTab, setFirstLaunch, setTheme } = useAppStore();
  const [simulatorOpen, setSimulatorOpen] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        const flRes = await fetch('/api/settings/first-launch');
        const flData = await flRes.json();
        if (flData.first_launch) {
          setFirstLaunch(true);
          setActiveTab('settings');
        }

        const settingsRes = await fetch('/api/settings');
        const settings = await settingsRes.json();
        if (settings.theme) setTheme(settings.theme);
      } catch {
        /* server not ready */
      }
    };
    init();
  }, []);

  const renderTab = () => {
    switch (activeTab) {
      case 'bots':
        return (
          <ErrorBoundary name="Bot List">
            <BotListPanel />
          </ErrorBoundary>
        );
      case 'editor':
        return (
          <ErrorBoundary name="Rule Editor">
            <div className="flex flex-col md:flex-row h-full">
              <div className="flex-1 min-w-0 min-h-0">
                <RuleEditor onOpenSimulator={() => setSimulatorOpen(true)} />
              </div>
              <SimulatorPanel open={simulatorOpen} onClose={() => setSimulatorOpen(false)} />
            </div>
          </ErrorBoundary>
        );
      case 'simulator':
        return (
          <ErrorBoundary name="Simulator">
            <div className="flex flex-col md:flex-row h-full">
              <div className="flex-1 min-w-0 min-h-0 hidden md:block">
                <RuleEditor onOpenSimulator={() => setSimulatorOpen(true)} />
              </div>
              <SimulatorPanel open={true} onClose={() => setActiveTab('editor')} />
            </div>
          </ErrorBoundary>
        );
      case 'markets':
        return (
          <ErrorBoundary name="Market Browser">
            <MarketBrowser />
          </ErrorBoundary>
        );
      case 'portfolio':
        return (
          <ErrorBoundary name="Portfolio">
            <PortfolioScreen />
          </ErrorBoundary>
        );
      case 'log':
        return (
          <ErrorBoundary name="Trade Log">
            <TradeLog />
          </ErrorBoundary>
        );
      case 'vars':
        return (
          <ErrorBoundary name="Live variables">
            <VarsPanel />
          </ErrorBoundary>
        );
      case 'settings':
        return (
          <ErrorBoundary name="Settings">
            <SettingsScreen />
          </ErrorBoundary>
        );
      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-terminal-bg">
      <div className="scanlines" aria-hidden="true" />
      <div className="hidden md:block">
        <SentimentStrip />
      </div>
      <TopNav />
      <main className="flex-1 overflow-hidden pb-14 md:pb-0">{renderTab()}</main>
      <BottomNav />
    </div>
  );
}
