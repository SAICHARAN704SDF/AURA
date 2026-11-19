"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, send, type Profile } from "../lib/api";
import { Section, ErrorLine } from "./Panels";
export default function Settings({
  project,
  switchProject,
}: {
  project: string;
  switchProject: (p: string) => void;
}) {
  const [id, setId] = useState(project);
  const [error, setError] = useState<unknown>();
  const [saved, setSaved] = useState(false);
  const [prefs, setPrefs] = useState<Profile | null>(null);
  const profile = useQuery({
    queryKey: ["profile", project],
    queryFn: () => api<Profile>("/projects/" + project + "/profile"),
  });
  const values = prefs ?? profile.data;
  return (
    <div className="columns">
      <Section title="Preferences">
        <ErrorLine error={profile.error ?? error} />
        {values && (
          <form
            className="stack"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await send(
                  "/projects/" + project + "/profile",
                  values,
                  undefined,
                  "PUT",
                );
                await profile.refetch();
                setSaved(true);
                setError(null);
              } catch (e) {
                setError(e);
              }
            }}
          >
            <label>
              Research preferences
              <textarea
                maxLength={500}
                value={values.preferences}
                onChange={(e) => {
                  setSaved(false);
                  setPrefs({ ...values, preferences: e.target.value });
                }}
              />
            </label>
            <label className="inline">
              <input
                type="checkbox"
                checked={values.adaptive_retrieval}
                onChange={(e) => {
                  setSaved(false);
                  setPrefs({ ...values, adaptive_retrieval: e.target.checked });
                }}
              />
              Use source feedback in search ranking
            </label>
            <button className="primary">Save preferences</button>
            {saved && <p role="status">Preferences saved.</p>}
          </form>
        )}
      </Section>
      <Section title="Switch project">
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            try {
              switchProject(id);
            } catch (e) {
              setError(e);
            }
          }}
        >
          <label>
            Project ID
            <input value={id} onChange={(e) => setId(e.target.value)} />
          </label>
          <button>Open project</button>
        </form>
      </Section>
    </div>
  );
}
