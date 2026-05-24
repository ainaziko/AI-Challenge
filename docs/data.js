/* Fake leaderboard data.
   None of the names, roles, or activities below are real. Categories have
   been renamed from the original to be safe (Mentorship / Talks / Outreach /
   Open Source). Avatars are initials in coloured circles — no photos.
*/

(function () {
  "use strict";

  // Activity categories shown in the filter dropdown and the row chips.
  const CATEGORIES = ["Mentorship", "Talks", "Outreach", "Open Source"];

  // 14 fictional employees with a varied mix of activities.
  // Each activity has: title, category, date (YYYY-MM-DD), points.
  const PEOPLE = [
    {
      id: 1,
      name: "Marlow Vance",
      role: "Engineering Lead",
      activities: [
        { title: "[CONF] Distributed Systems Day talk: cache invalidation patterns", category: "Talks", date: "2025-11-04", points: 64 },
        { title: "[TALK] Internal lightning talk: tracing in production", category: "Talks", date: "2025-09-18", points: 32 },
        { title: "[MNT] Mentoring three new grads through onboarding", category: "Mentorship", date: "2025-08-12", points: 64 },
        { title: "[SESH] Workshop: refactoring legacy services", category: "Talks", date: "2025-06-22", points: 32 },
        { title: "[MNT] Pair programming series — 6 sessions", category: "Mentorship", date: "2025-05-10", points: 48 },
        { title: "[OUT] Campus talk at Northvale Tech", category: "Outreach", date: "2025-04-15", points: 64 },
        { title: "[OSS] Reviewed PRs on a public observability library", category: "Open Source", date: "2025-03-08", points: 32 },
        { title: "[TALK] Brown-bag session: error budgets explained", category: "Talks", date: "2025-02-19", points: 32 },
        { title: "[MNT] Mock interview drills for the hiring loop", category: "Mentorship", date: "2025-01-26", points: 32 },
        { title: "[OUT] Hosted booth at the Open Engineering Fair", category: "Outreach", date: "2024-11-12", points: 64 },
      ],
    },
    {
      id: 2,
      name: "Indira Whitfield",
      role: "Senior Engineer",
      activities: [
        { title: "[TALK] Frontend Friday: state machines in React", category: "Talks", date: "2025-10-31", points: 32 },
        { title: "[MNT] Mentoring of Bryce Ackerman", category: "Mentorship", date: "2025-09-20", points: 64 },
        { title: "[MNT] Mentoring of Hana Petrenko", category: "Mentorship", date: "2025-09-20", points: 64 },
        { title: "[SESH] Workshop: TypeScript advanced types", category: "Talks", date: "2025-07-14", points: 32 },
        { title: "[OSS] Maintained the team's UI component library", category: "Open Source", date: "2025-05-30", points: 32 },
        { title: "[OUT] Career talk at Greenbridge Polytechnic", category: "Outreach", date: "2025-04-04", points: 64 },
        { title: "[TALK] Lightning talk: animations without re-renders", category: "Talks", date: "2025-02-07", points: 16 },
        { title: "[MNT] Code-review buddy programme — Q4", category: "Mentorship", date: "2024-12-18", points: 32 },
      ],
    },
    {
      id: 3,
      name: "Theo Brennan",
      role: "Quality Engineering Manager",
      activities: [
        { title: "[REG] Offline meetup: shift-left testing in practice", category: "Talks", date: "2025-10-10", points: 64 },
        { title: "[SESH] Workshop #1: Playwright fundamentals", category: "Talks", date: "2025-09-05", points: 16 },
        { title: "[SESH] Workshop #2: Playwright fixtures", category: "Talks", date: "2025-09-05", points: 16 },
        { title: "[SESH] Workshop #3: Visual regression testing", category: "Talks", date: "2025-09-05", points: 16 },
        { title: "[MNT] Mentoring of Joaquim Ribeiro", category: "Mentorship", date: "2025-08-02", points: 64 },
        { title: "[MNT] Mentoring of Naomi Eze", category: "Mentorship", date: "2025-08-02", points: 64 },
        { title: "[OUT] University demo day judging panel", category: "Outreach", date: "2025-05-22", points: 32 },
        { title: "[TALK] Brown-bag: flaky tests post-mortem", category: "Talks", date: "2025-03-14", points: 32 },
      ],
    },
    {
      id: 4,
      name: "Felix Marquez",
      role: "Product Designer",
      activities: [
        { title: "[TALK] Design crit: a year of usability findings", category: "Talks", date: "2025-12-02", points: 32 },
        { title: "[SESH] Workshop: design tokens 101", category: "Talks", date: "2025-10-15", points: 16 },
        { title: "[MNT] Mentoring of Saoirse Lindgren", category: "Mentorship", date: "2025-08-25", points: 64 },
        { title: "[OUT] Portfolio review evening for Bridgepoint Design School", category: "Outreach", date: "2025-06-11", points: 64 },
        { title: "[TALK] Design Friday: motion principles", category: "Talks", date: "2025-04-19", points: 32 },
        { title: "[OSS] Shipped Figma plug-in for accessible colour pairs", category: "Open Source", date: "2025-02-04", points: 32 },
      ],
    },
    {
      id: 5,
      name: "Niko Halverson",
      role: "Senior Backend Engineer",
      activities: [
        { title: "[TALK] Internal tech talk: building a search index", category: "Talks", date: "2025-11-22", points: 32 },
        { title: "[SESH] Workshop: SQL query plans", category: "Talks", date: "2025-09-08", points: 32 },
        { title: "[MNT] Mentoring of Mateusz Karczewski", category: "Mentorship", date: "2025-07-30", points: 64 },
        { title: "[OUT] Campus visit at Halberg State", category: "Outreach", date: "2025-05-05", points: 64 },
        { title: "[OSS] Open source contribution: tiny ORM helper", category: "Open Source", date: "2025-02-28", points: 32 },
      ],
    },
    {
      id: 6,
      name: "Priya Wendover",
      role: "Engineering Manager",
      activities: [
        { title: "[TALK] Career panel: from IC to manager", category: "Talks", date: "2025-12-15", points: 32 },
        { title: "[MNT] Mentoring of Calum Nardini", category: "Mentorship", date: "2025-10-18", points: 64 },
        { title: "[MNT] Mentoring of Mira Acheson", category: "Mentorship", date: "2025-10-18", points: 64 },
        { title: "[OUT] Hosted high-schoolers for a shadow day", category: "Outreach", date: "2025-06-07", points: 32 },
        { title: "[TALK] Brown-bag: writing readable PR descriptions", category: "Talks", date: "2025-03-25", points: 16 },
      ],
    },
    {
      id: 7,
      name: "Tamsin Holloway",
      role: "Staff Data Engineer",
      activities: [
        { title: "[TALK] Internal: streaming pipelines without tears", category: "Talks", date: "2025-09-30", points: 32 },
        { title: "[SESH] Workshop: incremental ETL patterns", category: "Talks", date: "2025-08-14", points: 32 },
        { title: "[OUT] Data career fair at Coral Heights University", category: "Outreach", date: "2025-05-28", points: 64 },
        { title: "[MNT] Mentoring of Ola Gjerde", category: "Mentorship", date: "2025-04-09", points: 64 },
        { title: "[OSS] Documentation overhaul for a public dbt package", category: "Open Source", date: "2025-01-21", points: 32 },
      ],
    },
    {
      id: 8,
      name: "Soren Bardeau",
      role: "DevOps Engineer",
      activities: [
        { title: "[TALK] Lightning talk: dependency-free Bash logging", category: "Talks", date: "2025-11-11", points: 16 },
        { title: "[MNT] Mentoring of Pavel Sklyarov", category: "Mentorship", date: "2025-09-14", points: 64 },
        { title: "[SESH] Workshop: writing better Makefiles", category: "Talks", date: "2025-06-18", points: 16 },
        { title: "[OUT] Tech talk at the local Linux user group", category: "Outreach", date: "2025-03-03", points: 32 },
      ],
    },
    {
      id: 9,
      name: "Lin Pemberton",
      role: "Frontend Engineer",
      activities: [
        { title: "[TALK] Brown-bag: CSS container queries in practice", category: "Talks", date: "2025-10-08", points: 16 },
        { title: "[SESH] Workshop: building accessible modals", category: "Talks", date: "2025-08-29", points: 32 },
        { title: "[MNT] Mentoring of Quentin Bayle", category: "Mentorship", date: "2025-07-01", points: 64 },
        { title: "[OUT] Talk at the Mistral Code Bootcamp", category: "Outreach", date: "2025-04-12", points: 32 },
      ],
    },
    {
      id: 10,
      name: "Yara Castellano",
      role: "Tech Lead",
      activities: [
        { title: "[CONF] Conference keynote: ten years of incremental rollouts", category: "Talks", date: "2025-09-26", points: 64 },
        { title: "[SESH] Workshop: feature flags without footguns", category: "Talks", date: "2025-07-19", points: 32 },
        { title: "[TALK] Brown-bag: writing post-mortems", category: "Talks", date: "2025-05-16", points: 16 },
        { title: "[OUT] Career panel at Indigo Tech University", category: "Outreach", date: "2025-02-13", points: 32 },
      ],
    },
    {
      id: 11,
      name: "Reed Okonkwo",
      role: "Security Engineer",
      activities: [
        { title: "[TALK] Security 101 for product teams", category: "Talks", date: "2025-10-24", points: 32 },
        { title: "[SESH] Workshop: threat modeling in 60 minutes", category: "Talks", date: "2025-09-12", points: 32 },
        { title: "[MNT] Mentoring of Adaeze Bello", category: "Mentorship", date: "2025-08-20", points: 64 },
      ],
    },
    {
      id: 12,
      name: "Sage Lindqvist",
      role: "Product Manager",
      activities: [
        { title: "[TALK] Product discovery deep-dive", category: "Talks", date: "2025-09-02", points: 32 },
        { title: "[MNT] Mentoring of two early-career PMs", category: "Mentorship", date: "2025-06-04", points: 64 },
        { title: "[OUT] Hosted product strategy session at GoldField MBA", category: "Outreach", date: "2025-03-19", points: 64 },
      ],
    },
    {
      id: 13,
      name: "Ash Tagawa",
      role: "Mobile Engineer",
      activities: [
        { title: "[TALK] Mobile Monday: animation performance tips", category: "Talks", date: "2025-08-04", points: 16 },
        { title: "[MNT] Mentoring of Marcin Lewicki", category: "Mentorship", date: "2025-05-22", points: 64 },
        { title: "[OSS] Contributed a fix to a popular Compose library", category: "Open Source", date: "2025-02-26", points: 32 },
      ],
    },
    {
      id: 14,
      name: "Jules Caldera",
      role: "Engineering Manager",
      activities: [
        { title: "[REG] Offline meetup: managers' roundtable", category: "Talks", date: "2024-11-30", points: 64 },
        { title: "[MNT] Mentoring of Saskia Vermeer", category: "Mentorship", date: "2024-10-08", points: 64 },
        { title: "[TALK] Brown-bag: hiring without bias", category: "Talks", date: "2024-08-15", points: 32 },
        { title: "[OUT] Speaker at Brightlake University career week", category: "Outreach", date: "2024-05-04", points: 64 },
      ],
    },
  ];

  // Public namespace consumed by app.js.
  window.LEADERBOARD_DATA = {
    categories: CATEGORIES,
    people: PEOPLE,
  };
})();
